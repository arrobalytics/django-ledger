"""
High-level API tests for InvoiceModel payment, void, cancel, and delete behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_RECEIVABLES,
    COGS,
    INCOME_OPERATIONAL,
    LIABILITY_CL_DEFERRED_REVENUE,
)
from django_ledger.models import InvoiceModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModelValidationError
from django_ledger.models.items import ItemModel


class InvoicePaymentVoidDeleteAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_invoice_payment_user",
            email="api-invoice-payment-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Invoice Payment Entity"):
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
            code="1210",
            name=f"{name} Receivable Account",
            role=ASSET_CA_RECEIVABLES,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="2310",
            name=f"{name} Deferred Revenue Account",
            role=LIABILITY_CL_DEFERRED_REVENUE,
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="5010",
            name=f"{name} COGS Account",
            role=COGS,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="4010",
            name=f"{name} Income Account",
            role=INCOME_OPERATIONAL,
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f"{name} Unit",
            unit_abbr=f"i-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )
        customer_model = CustomerModel(
            customer_name=f"{name} Customer",
            entity_model=entity_model,
            description=f"{name} customer.",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "customer_model": customer_model,
            "service_item": service_item,
        }

    def create_invoice(self, setup):
        invoice_model = setup["entity_model"].create_invoice(
            customer_model=setup["customer_model"],
            terms=InvoiceModel.TERMS_NET_30,
            date_draft=date(2025, 1, 15),
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def migrate_service_item(self, invoice_model, setup, *, total_amount=Decimal("100.00")):
        invoice_model.migrate_itemtxs(
            itemtxs={
                setup["service_item"].item_number: {
                    "quantity": Decimal("1.00"),
                    "unit_cost": total_amount,
                    "total_amount": total_amount,
                }
            },
            operation=InvoiceModel.ITEMIZE_REPLACE,
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def make_review_invoice(self, setup):
        invoice_model = self.migrate_service_item(self.create_invoice(setup), setup)
        invoice_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        invoice_model.refresh_from_db()
        return invoice_model

    def make_approved_invoice(self, setup):
        invoice_model = self.make_review_invoice(setup)
        invoice_model.mark_as_approved(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_approved=date(2025, 1, 17),
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def make_paid_invoice(self, setup):
        invoice_model = self.make_approved_invoice(setup)
        invoice_model.mark_as_paid(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_paid=date(2025, 1, 18),
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def test_make_payment_partial_commit_true_updates_amounts_without_paid_status(self):
        setup = self.create_entity_setup(name="API Invoice Payment Partial Entity")
        invoice_model = self.make_approved_invoice(setup)

        invoice_model.make_payment(
            payment_amount=Decimal("25.00"),
            payment_date=date(2025, 1, 18),
            commit=True,
        )
        invoice_model.refresh_from_db()

        self.assertTrue(invoice_model.is_approved())
        self.assertEqual(invoice_model.amount_paid, Decimal("25.00"))
        self.assertEqual(invoice_model.amount_due, Decimal("100.00"))
        self.assertTrue(invoice_model.can_make_payment())

    def test_make_payment_accepts_payment_date_before_approval_as_current_behavior(self):
        setup = self.create_entity_setup(name="API Invoice Payment Early Entity")
        invoice_model = self.make_approved_invoice(setup)

        invoice_model.make_payment(
            payment_amount=Decimal("25.00"),
            payment_date=date(2025, 1, 16),
            commit=True,
        )
        invoice_model.refresh_from_db()

        self.assertEqual(invoice_model.date_approved, date(2025, 1, 17))
        self.assertEqual(invoice_model.amount_paid, Decimal("25.00"))

    def test_make_payment_rejects_overpayment_and_characterizes_no_raise_path(self):
        setup = self.create_entity_setup(name="API Invoice Payment Overpay Entity")
        invoice_model = self.make_approved_invoice(setup)

        with self.assertRaises(InvoiceModelValidationError):
            invoice_model.make_payment(payment_amount=Decimal("150.00"), commit=True)
        self.assertGreater(invoice_model.amount_paid, invoice_model.amount_due)
        invoice_model.refresh_from_db()
        self.assertEqual(invoice_model.amount_paid, Decimal("0.00"))

        invoice_model.make_payment(
            payment_amount=Decimal("150.00"),
            commit=True,
            raise_exception=False,
        )
        self.assertGreater(invoice_model.amount_paid, invoice_model.amount_due)
        invoice_model.refresh_from_db()
        self.assertEqual(invoice_model.amount_paid, Decimal("0.00"))

    def test_mark_as_paid_pays_invoice_and_locks_ledger(self):
        setup = self.create_entity_setup(name="API Invoice Payment Paid Entity")
        invoice_model = self.make_approved_invoice(setup)

        invoice_model.mark_as_paid(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_paid=date(2025, 1, 18),
            commit=True,
        )
        invoice_model.refresh_from_db()

        self.assertTrue(invoice_model.is_paid())
        self.assertEqual(invoice_model.amount_paid, invoice_model.amount_due)
        self.assertEqual(invoice_model.date_paid, date(2025, 1, 18))
        self.assertTrue(invoice_model.ledger.locked)

    def test_mark_as_void_voids_unpaid_approved_invoice_and_locks_ledger(self):
        setup = self.create_entity_setup(name="API Invoice Payment Void Entity")
        invoice_model = self.make_approved_invoice(setup)

        invoice_model.mark_as_void(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_void=date(2025, 1, 19),
            commit=True,
        )
        invoice_model.refresh_from_db()

        self.assertTrue(invoice_model.is_void())
        self.assertEqual(invoice_model.date_void, date(2025, 1, 19))
        self.assertEqual(invoice_model.amount_paid, Decimal("0.00"))
        self.assertEqual(invoice_model.amount_due, Decimal("100.00"))
        self.assertTrue(invoice_model.ledger.locked)

    def test_cancel_rejects_active_invoices_and_allows_draft_or_review_invoices(self):
        setup = self.create_entity_setup(name="API Invoice Payment Cancel Entity")

        draft_invoice = self.create_invoice(setup)
        draft_invoice.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))
        draft_invoice.refresh_from_db()
        self.assertTrue(draft_invoice.is_canceled())

        review_invoice = self.make_review_invoice(setup)
        review_invoice.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 21))
        review_invoice.refresh_from_db()
        self.assertTrue(review_invoice.is_canceled())

        approved_invoice = self.make_approved_invoice(setup)
        with self.assertRaises(InvoiceModelValidationError):
            approved_invoice.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 22))
        approved_invoice.refresh_from_db()
        self.assertTrue(approved_invoice.is_approved())

    def test_delete_defaults_to_cancel_and_force_delete_removes_deletable_invoice(self):
        setup = self.create_entity_setup(name="API Invoice Payment Delete Entity")

        cancel_invoice = self.create_invoice(setup)
        cancel_invoice.delete()
        cancel_invoice.refresh_from_db()
        self.assertTrue(cancel_invoice.is_canceled())

        delete_invoice = self.create_invoice(setup)
        delete_uuid = delete_invoice.uuid
        delete_invoice.delete(force_db_delete=True)
        self.assertFalse(InvoiceModel.objects.filter(uuid=delete_uuid).exists())

    def test_force_delete_rejects_locked_paid_invoice_and_leaves_it_intact(self):
        setup = self.create_entity_setup(name="API Invoice Payment Delete Guard Entity")
        paid_invoice = self.make_paid_invoice(setup)
        paid_uuid = paid_invoice.uuid

        with self.assertRaises(InvoiceModelValidationError):
            paid_invoice.delete(force_db_delete=True)

        persisted_invoice = InvoiceModel.objects.get(uuid=paid_uuid)
        self.assertTrue(persisted_invoice.is_paid())
        self.assertTrue(persisted_invoice.ledger.locked)
