"""
High-level API tests for InvoiceModel lifecycle transitions.
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
from django_ledger.models import InvoiceModel, ItemTransactionModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModelValidationError
from django_ledger.models.items import ItemModel


class InvoiceLifecycleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_invoice_lifecycle_user",
            email="api-invoice-lifecycle-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Invoice Lifecycle Entity"):
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

    def create_invoice(self, setup, *, date_draft=date(2025, 1, 15)):
        invoice_model = setup["entity_model"].create_invoice(
            customer_model=setup["customer_model"],
            terms=InvoiceModel.TERMS_NET_30,
            date_draft=date_draft,
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

    def test_valid_status_transitions_set_dates_and_ledger_state(self):
        setup = self.create_entity_setup(name="API Invoice Lifecycle Valid Entity")
        invoice_model = self.migrate_service_item(self.create_invoice(setup), setup)

        invoice_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        invoice_model.refresh_from_db()
        self.assertTrue(invoice_model.is_review())
        self.assertEqual(invoice_model.date_in_review, date(2025, 1, 16))
        self.assertFalse(invoice_model.ledger.posted)

        invoice_model.mark_as_approved(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_approved=date(2025, 1, 17),
            commit=True,
        )
        invoice_model.refresh_from_db()
        self.assertTrue(invoice_model.is_approved())
        self.assertEqual(invoice_model.date_approved, date(2025, 1, 17))
        self.assertEqual(invoice_model.date_due, date(2025, 2, 16))
        self.assertTrue(invoice_model.ledger.posted)
        self.assertFalse(invoice_model.ledger.locked)

        invoice_model.mark_as_paid(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_paid=date(2025, 1, 18),
            commit=True,
        )
        invoice_model.refresh_from_db()
        self.assertTrue(invoice_model.is_paid())
        self.assertEqual(invoice_model.date_paid, date(2025, 1, 18))
        self.assertEqual(invoice_model.amount_paid, invoice_model.amount_due)
        self.assertTrue(invoice_model.ledger.locked)

    def test_mark_as_draft_returns_review_invoice_to_draft_and_sets_draft_date(self):
        setup = self.create_entity_setup(name="API Invoice Lifecycle Draft Entity")
        invoice_model = self.make_review_invoice(setup)

        invoice_model.mark_as_draft(draft_date=date(2025, 1, 19), commit=True)
        invoice_model.refresh_from_db()

        self.assertTrue(invoice_model.is_draft())
        self.assertEqual(invoice_model.date_draft, date(2025, 1, 19))

    def test_cancel_and_void_transitions_set_terminal_status_dates(self):
        setup = self.create_entity_setup(name="API Invoice Lifecycle Terminal Entity")

        draft_invoice = self.create_invoice(setup)
        draft_invoice.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))
        draft_invoice.refresh_from_db()
        self.assertTrue(draft_invoice.is_canceled())
        self.assertEqual(draft_invoice.date_canceled, date(2025, 1, 20))

        review_invoice = self.make_review_invoice(setup)
        review_invoice.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 21))
        review_invoice.refresh_from_db()
        self.assertTrue(review_invoice.is_canceled())
        self.assertEqual(review_invoice.date_canceled, date(2025, 1, 21))

        approved_invoice = self.make_approved_invoice(setup)
        approved_invoice.mark_as_void(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_void=date(2025, 1, 22),
            commit=True,
        )
        approved_invoice.refresh_from_db()
        self.assertTrue(approved_invoice.is_void())
        self.assertEqual(approved_invoice.date_void, date(2025, 1, 22))
        self.assertEqual(approved_invoice.amount_paid, Decimal("0.00"))
        self.assertTrue(approved_invoice.ledger.locked)

    def test_invalid_transitions_raise_validation_errors(self):
        setup = self.create_entity_setup(name="API Invoice Lifecycle Invalid Entity")
        draft_invoice = self.create_invoice(setup)

        with self.assertRaises(InvoiceModelValidationError):
            draft_invoice.mark_as_paid(
                entity_slug=setup["entity_model"].slug,
                user_model=self.user,
                date_paid=date(2025, 1, 18),
                commit=True,
            )

        paid_invoice = self.make_paid_invoice(setup)
        with self.assertRaises(InvoiceModelValidationError):
            paid_invoice.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 19))
        with self.assertRaises(InvoiceModelValidationError):
            paid_invoice.mark_as_void(
                entity_slug=setup["entity_model"].slug,
                user_model=self.user,
                date_void=date(2025, 1, 19),
                commit=True,
            )

        canceled_invoice = self.create_invoice(setup)
        canceled_invoice.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))
        with self.assertRaises(InvoiceModelValidationError):
            canceled_invoice.mark_as_review(commit=True, date_in_review=date(2025, 1, 21))

    def test_can_predicates_reflect_status_transitions(self):
        setup = self.create_entity_setup(name="API Invoice Lifecycle Predicate Entity")
        draft_invoice = self.create_invoice(setup)

        self.assertFalse(draft_invoice.can_draft())
        self.assertTrue(draft_invoice.can_review())
        self.assertFalse(draft_invoice.can_approve())
        self.assertFalse(draft_invoice.can_pay())
        self.assertFalse(draft_invoice.can_void())
        self.assertTrue(draft_invoice.can_cancel())

        review_invoice = self.make_review_invoice(setup)
        self.assertTrue(review_invoice.can_draft())
        self.assertTrue(review_invoice.can_approve())
        self.assertFalse(review_invoice.can_pay())
        self.assertFalse(review_invoice.can_void())
        self.assertTrue(review_invoice.can_cancel())

        approved_invoice = self.make_approved_invoice(setup)
        self.assertFalse(approved_invoice.can_draft())
        self.assertFalse(approved_invoice.can_approve())
        self.assertTrue(approved_invoice.can_pay())
        self.assertTrue(approved_invoice.can_void())
        self.assertFalse(approved_invoice.can_cancel())

        paid_invoice = self.make_paid_invoice(setup)
        self.assertFalse(paid_invoice.can_pay())
        self.assertFalse(paid_invoice.can_void())
        self.assertFalse(paid_invoice.can_cancel())

    def test_commit_false_transitions_mutate_in_memory_without_persisting(self):
        setup = self.create_entity_setup(name="API Invoice Lifecycle Commit False Entity")
        invoice_model = self.migrate_service_item(self.create_invoice(setup), setup)

        invoice_model.mark_as_review(commit=False, date_in_review=date(2025, 1, 16))
        self.assertTrue(invoice_model.is_review())
        self.assertEqual(invoice_model.date_in_review, date(2025, 1, 16))
        db_invoice = InvoiceModel.objects.get(uuid=invoice_model.uuid)
        self.assertTrue(db_invoice.is_draft())
        self.assertIsNone(db_invoice.date_in_review)

        invoice_model.refresh_from_db()
        invoice_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        invoice_model.refresh_from_db()
        invoice_model.mark_as_approved(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_approved=date(2025, 1, 17),
            commit=False,
        )
        self.assertTrue(invoice_model.is_approved())
        self.assertEqual(invoice_model.date_approved, date(2025, 1, 17))
        db_invoice = InvoiceModel.objects.get(uuid=invoice_model.uuid)
        self.assertTrue(db_invoice.is_review())
        self.assertIsNone(db_invoice.date_approved)
        self.assertFalse(db_invoice.ledger.posted)

    def test_review_rejects_invoice_without_items(self):
        setup = self.create_entity_setup(name="API Invoice Lifecycle No Items Entity")
        invoice_model = self.create_invoice(setup)

        with self.assertRaises(InvoiceModelValidationError):
            invoice_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

        self.assertFalse(ItemTransactionModel.objects.filter(invoice_model=invoice_model).exists())
