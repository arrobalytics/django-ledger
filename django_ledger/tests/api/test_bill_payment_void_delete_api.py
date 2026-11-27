"""
High-level API tests for BillModel payment, void, cancel, and delete behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_PREPAID,
    EXPENSE_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
)
from django_ledger.models import BillModel
from django_ledger.models.bill import BillModelValidationError
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel


class BillPaymentVoidDeleteAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_bill_payment_user",
            email="api-bill-payment-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Bill Payment Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        coa_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role=ASSET_CA_CASH,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="1310",
            name=f"{name} Prepaid Account",
            role=ASSET_CA_PREPAID,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="2010",
            name=f"{name} Accounts Payable",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role=EXPENSE_OPERATIONAL,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f"{name} Unit",
            unit_abbr=f"b-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )
        vendor_model = entity_model.create_vendor(
            {
                "vendor_name": f"{name} Vendor",
                "description": f"{name} vendor.",
                "active": True,
                "hidden": False,
            },
            commit=True,
        )
        expense_item = entity_model.create_item_expense(
            name=f"{name} Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "vendor_model": vendor_model,
            "expense_item": expense_item,
        }

    def create_bill(self, setup):
        bill_model = setup["entity_model"].create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_NET_30,
            date_draft=date(2025, 1, 15),
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def migrate_expense_item(self, bill_model, setup, *, total_amount=Decimal("100.00")):
        bill_model.migrate_itemtxs(
            itemtxs={
                setup["expense_item"].item_number: {
                    "quantity": Decimal("1.00"),
                    "unit_cost": total_amount,
                    "total_amount": total_amount,
                }
            },
            operation=BillModel.ITEMIZE_REPLACE,
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def make_review_bill(self, setup):
        bill_model = self.migrate_expense_item(self.create_bill(setup), setup)
        bill_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        bill_model.refresh_from_db()
        return bill_model

    def make_approved_bill(self, setup):
        bill_model = self.make_review_bill(setup)
        bill_model.mark_as_approved(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_approved=date(2025, 1, 17),
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def make_paid_bill(self, setup):
        bill_model = self.make_approved_bill(setup)
        bill_model.mark_as_paid(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_paid=date(2025, 1, 18),
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def test_make_payment_partial_commit_true_updates_amounts_without_paid_status(self):
        setup = self.create_entity_setup(name="API Bill Payment Partial Entity")
        bill_model = self.make_approved_bill(setup)

        bill_model.make_payment(
            payment_amount=Decimal("25.00"),
            payment_date=date(2025, 1, 18),
            commit=True,
        )
        bill_model.refresh_from_db()

        self.assertTrue(bill_model.is_approved())
        self.assertEqual(bill_model.amount_paid, Decimal("25.00"))
        self.assertEqual(bill_model.amount_due, Decimal("100.00"))
        self.assertTrue(bill_model.can_make_payment())

    def test_make_payment_rejects_overpayment_and_characterizes_no_raise_path(self):
        setup = self.create_entity_setup(name="API Bill Payment Overpay Entity")
        bill_model = self.make_approved_bill(setup)

        with self.assertRaises(BillModelValidationError):
            bill_model.make_payment(payment_amount=Decimal("150.00"), commit=True)
        self.assertGreater(bill_model.amount_paid, bill_model.amount_due)
        bill_model.refresh_from_db()
        self.assertEqual(bill_model.amount_paid, Decimal("0.00"))

        bill_model.make_payment(
            payment_amount=Decimal("150.00"),
            commit=True,
            raise_exception=False,
        )
        self.assertGreater(bill_model.amount_paid, bill_model.amount_due)
        bill_model.refresh_from_db()
        self.assertEqual(bill_model.amount_paid, Decimal("0.00"))

    def test_mark_as_paid_pays_bill_and_locks_ledger(self):
        setup = self.create_entity_setup(name="API Bill Payment Paid Entity")
        bill_model = self.make_approved_bill(setup)

        bill_model.mark_as_paid(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_paid=date(2025, 1, 18),
            commit=True,
        )
        bill_model.refresh_from_db()

        self.assertTrue(bill_model.is_paid())
        self.assertEqual(bill_model.amount_paid, bill_model.amount_due)
        self.assertEqual(bill_model.date_paid, date(2025, 1, 18))
        self.assertTrue(bill_model.ledger.locked)

    def test_mark_as_void_voids_unpaid_approved_bill_and_characterizes_ledger_lock(self):
        setup = self.create_entity_setup(name="API Bill Payment Void Entity")
        bill_model = self.make_approved_bill(setup)

        bill_model.mark_as_void(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_void=date(2025, 1, 19),
            commit=True,
        )
        in_memory_locked = bill_model.ledger.locked
        bill_model.refresh_from_db()

        self.assertTrue(bill_model.is_void())
        self.assertEqual(bill_model.date_void, date(2025, 1, 19))
        self.assertEqual(bill_model.amount_paid, Decimal("0.00"))
        self.assertEqual(bill_model.amount_due, Decimal("100.00"))
        self.assertTrue(in_memory_locked)
        self.assertFalse(bill_model.ledger.locked)

    def test_cancel_rejects_active_bills_and_allows_draft_or_review_bills(self):
        setup = self.create_entity_setup(name="API Bill Payment Cancel Entity")

        draft_bill = self.create_bill(setup)
        draft_bill.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))
        draft_bill.refresh_from_db()
        self.assertTrue(draft_bill.is_canceled())

        review_bill = self.make_review_bill(setup)
        review_bill.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 21))
        review_bill.refresh_from_db()
        self.assertTrue(review_bill.is_canceled())

        approved_bill = self.make_approved_bill(setup)
        with self.assertRaises(BillModelValidationError):
            approved_bill.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 22))
        approved_bill.refresh_from_db()
        self.assertTrue(approved_bill.is_approved())

    def test_delete_defaults_to_cancel_and_force_delete_removes_deletable_bill(self):
        setup = self.create_entity_setup(name="API Bill Payment Delete Entity")

        cancel_bill = self.create_bill(setup)
        cancel_bill.delete()
        cancel_bill.refresh_from_db()
        self.assertTrue(cancel_bill.is_canceled())

        delete_bill = self.create_bill(setup)
        delete_uuid = delete_bill.uuid
        delete_bill.delete(force_db_delete=True)
        self.assertFalse(BillModel.objects.filter(uuid=delete_uuid).exists())

    def test_force_delete_rejects_locked_paid_bill_and_leaves_it_intact(self):
        setup = self.create_entity_setup(name="API Bill Payment Delete Guard Entity")
        paid_bill = self.make_paid_bill(setup)
        paid_uuid = paid_bill.uuid

        with self.assertRaises(BillModelValidationError):
            paid_bill.delete(force_db_delete=True)

        persisted_bill = BillModel.objects.get(uuid=paid_uuid)
        self.assertTrue(persisted_bill.is_paid())
        self.assertTrue(persisted_bill.ledger.locked)
