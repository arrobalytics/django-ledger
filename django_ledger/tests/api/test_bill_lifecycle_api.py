"""
High-level API tests for BillModel lifecycle transitions.
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
from django_ledger.models import BillModel, ItemTransactionModel
from django_ledger.models.bill import BillModelValidationError
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel


class BillLifecycleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_bill_lifecycle_user",
            email="api-bill-lifecycle-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Bill Lifecycle Entity"):
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

    def create_bill(self, setup, *, date_draft=date(2025, 1, 15)):
        bill_model = setup["entity_model"].create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_NET_30,
            date_draft=date_draft,
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

    def test_valid_status_transitions_set_dates_and_ledger_state(self):
        setup = self.create_entity_setup(name="API Bill Lifecycle Valid Entity")
        bill_model = self.migrate_expense_item(self.create_bill(setup), setup)

        bill_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        bill_model.refresh_from_db()
        self.assertTrue(bill_model.is_review())
        self.assertEqual(bill_model.date_in_review, date(2025, 1, 16))
        self.assertFalse(bill_model.ledger.posted)

        bill_model.mark_as_approved(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_approved=date(2025, 1, 17),
            commit=True,
        )
        bill_model.refresh_from_db()
        self.assertTrue(bill_model.is_approved())
        self.assertEqual(bill_model.date_approved, date(2025, 1, 17))
        self.assertTrue(bill_model.ledger.posted)
        self.assertFalse(bill_model.ledger.locked)

        bill_model.mark_as_paid(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_paid=date(2025, 1, 18),
            commit=True,
        )
        bill_model.refresh_from_db()
        self.assertTrue(bill_model.is_paid())
        self.assertEqual(bill_model.date_paid, date(2025, 1, 18))
        self.assertEqual(bill_model.amount_paid, bill_model.amount_due)
        self.assertTrue(bill_model.ledger.locked)

    def test_cancel_and_void_transitions_set_terminal_status_dates(self):
        setup = self.create_entity_setup(name="API Bill Lifecycle Terminal Entity")

        draft_bill = self.create_bill(setup)
        draft_bill.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))
        draft_bill.refresh_from_db()
        self.assertTrue(draft_bill.is_canceled())
        self.assertEqual(draft_bill.date_canceled, date(2025, 1, 20))

        review_bill = self.make_review_bill(setup)
        review_bill.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 21))
        review_bill.refresh_from_db()
        self.assertTrue(review_bill.is_canceled())
        self.assertEqual(review_bill.date_canceled, date(2025, 1, 21))

        approved_bill = self.make_approved_bill(setup)
        approved_bill.mark_as_void(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_void=date(2025, 1, 22),
            commit=True,
        )
        approved_bill.refresh_from_db()
        self.assertTrue(approved_bill.is_void())
        self.assertEqual(approved_bill.date_void, date(2025, 1, 22))
        self.assertEqual(approved_bill.amount_paid, Decimal("0.00"))

    def test_invalid_transitions_raise_validation_errors(self):
        setup = self.create_entity_setup(name="API Bill Lifecycle Invalid Entity")
        draft_bill = self.create_bill(setup)

        with self.assertRaises(BillModelValidationError):
            draft_bill.mark_as_paid(
                entity_slug=setup["entity_model"].slug,
                user_model=self.user,
                date_paid=date(2025, 1, 18),
                commit=True,
            )

        paid_bill = self.make_paid_bill(setup)
        with self.assertRaises(BillModelValidationError):
            paid_bill.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 19))
        with self.assertRaises(BillModelValidationError):
            paid_bill.mark_as_void(
                entity_slug=setup["entity_model"].slug,
                user_model=self.user,
                date_void=date(2025, 1, 19),
                commit=True,
            )

        canceled_bill = self.create_bill(setup)
        canceled_bill.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))
        with self.assertRaises(BillModelValidationError):
            canceled_bill.mark_as_review(commit=True, date_in_review=date(2025, 1, 21))

    def test_can_predicates_reflect_status_transitions(self):
        setup = self.create_entity_setup(name="API Bill Lifecycle Predicate Entity")
        draft_bill = self.create_bill(setup)

        self.assertFalse(draft_bill.can_draft())
        self.assertTrue(draft_bill.can_review())
        self.assertFalse(draft_bill.can_approve())
        self.assertFalse(draft_bill.can_pay())
        self.assertFalse(draft_bill.can_void())
        self.assertTrue(draft_bill.can_cancel())

        review_bill = self.make_review_bill(setup)
        self.assertTrue(review_bill.can_draft())
        self.assertTrue(review_bill.can_approve())
        self.assertFalse(review_bill.can_pay())
        self.assertFalse(review_bill.can_void())
        self.assertTrue(review_bill.can_cancel())

        approved_bill = self.make_approved_bill(setup)
        self.assertFalse(approved_bill.can_draft())
        self.assertFalse(approved_bill.can_approve())
        self.assertTrue(approved_bill.can_pay())
        self.assertTrue(approved_bill.can_void())
        self.assertFalse(approved_bill.can_cancel())

        paid_bill = self.make_paid_bill(setup)
        self.assertFalse(paid_bill.can_pay())
        self.assertFalse(paid_bill.can_void())
        self.assertFalse(paid_bill.can_cancel())

    def test_commit_false_transitions_mutate_in_memory_without_persisting(self):
        setup = self.create_entity_setup(name="API Bill Lifecycle Commit False Entity")
        bill_model = self.migrate_expense_item(self.create_bill(setup), setup)

        bill_model.mark_as_review(commit=False, date_in_review=date(2025, 1, 16))
        self.assertTrue(bill_model.is_review())
        self.assertEqual(bill_model.date_in_review, date(2025, 1, 16))
        db_bill = BillModel.objects.get(uuid=bill_model.uuid)
        self.assertTrue(db_bill.is_draft())
        self.assertIsNone(db_bill.date_in_review)

        bill_model.refresh_from_db()
        bill_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        bill_model.refresh_from_db()
        bill_model.mark_as_approved(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_approved=date(2025, 1, 17),
            commit=False,
        )
        self.assertTrue(bill_model.is_approved())
        self.assertEqual(bill_model.date_approved, date(2025, 1, 17))
        db_bill = BillModel.objects.get(uuid=bill_model.uuid)
        self.assertTrue(db_bill.is_review())
        self.assertIsNone(db_bill.date_approved)
        self.assertFalse(db_bill.ledger.posted)

    def test_review_rejects_bill_without_items(self):
        setup = self.create_entity_setup(name="API Bill Lifecycle No Items Entity")
        bill_model = self.create_bill(setup)

        with self.assertRaises(BillModelValidationError):
            bill_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

        self.assertFalse(ItemTransactionModel.objects.filter(bill_model=bill_model).exists())
