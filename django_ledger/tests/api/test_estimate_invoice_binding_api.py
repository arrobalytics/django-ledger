"""
High-level API tests for EstimateModel to InvoiceModel binding behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_INVENTORY,
    ASSET_CA_RECEIVABLES,
    COGS,
    INCOME_OPERATIONAL,
    LIABILITY_CL_DEFERRED_REVENUE,
)
from django_ledger.models import EstimateModel, InvoiceModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModelValidationError


class EstimateInvoiceBindingAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_estimate_invoice_binding_user",
            email="api-estimate-invoice-binding-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Estimate Invoice Binding Entity"):
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
            code="1410",
            name=f"{name} Inventory Account",
            role=ASSET_CA_INVENTORY,
            balance_type="debit",
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
            name=f"Unit {str(entity_model.uuid)[:8]}",
            unit_abbr=f"e-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )
        customer_model = self.create_customer(entity_model, name=f"{name} Customer")
        other_customer_model = self.create_customer(entity_model, name=f"{name} Other Customer")
        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "customer_model": customer_model,
            "other_customer_model": other_customer_model,
            "service_item": service_item,
        }

    def create_customer(self, entity_model, *, name):
        customer_model = CustomerModel(
            customer_name=name,
            entity_model=entity_model,
            description=f"{name} description.",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        return customer_model

    def create_estimate(self, setup, *, title="API Estimate Invoice Binding Contract"):
        estimate_model = setup["entity_model"].create_estimate(
            estimate_title=title,
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=setup["customer_model"],
            date_draft=date(2025, 1, 15),
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def migrate_service_item(self, estimate_model, setup):
        estimate_model.migrate_itemtxs(
            itemtxs={
                setup["service_item"].item_number: {
                    "quantity": Decimal("1.00"),
                    "unit_cost": Decimal("100.00"),
                    "unit_revenue": Decimal("150.00"),
                    "total_amount": Decimal("150.00"),
                }
            },
            operation=EstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def make_review_estimate(self, setup, *, title="API Review Estimate"):
        estimate_model = self.migrate_service_item(self.create_estimate(setup, title=title), setup)
        estimate_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        estimate_model.refresh_from_db()
        return estimate_model

    def make_approved_estimate(self, setup, *, title="API Approved Estimate"):
        estimate_model = self.make_review_estimate(setup, title=title)
        estimate_model.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))
        estimate_model.refresh_from_db()
        return estimate_model

    def create_invoice(self, setup, *, customer_model=None):
        invoice_model = setup["entity_model"].create_invoice(
            customer_model=customer_model or setup["customer_model"],
            terms=InvoiceModel.TERMS_NET_30,
            date_draft=date(2025, 1, 20),
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def test_approved_estimate_can_bind_to_invoice(self):
        setup = self.create_entity_setup()
        estimate_model = self.make_approved_estimate(setup)
        invoice_model = self.create_invoice(setup)

        self.assertTrue(invoice_model.can_bind_estimate(estimate_model))

        invoice_model.bind_estimate(estimate_model, commit=True)
        invoice_model.refresh_from_db()

        self.assertEqual(invoice_model.ce_model_id, estimate_model.uuid)
        self.assertEqual(invoice_model.customer_id, estimate_model.customer_id)
        self.assertTrue(estimate_model.invoicemodel_set.filter(uuid=invoice_model.uuid).exists())

    def test_unapproved_estimate_cannot_bind_to_invoice(self):
        setup = self.create_entity_setup(name="API Estimate Invoice Binding Unapproved Entity")
        draft_estimate = self.create_estimate(setup, title="API Draft Estimate")
        review_estimate = self.make_review_estimate(setup, title="API Review Estimate")
        invoice_model = self.create_invoice(setup)

        self.assertFalse(invoice_model.can_bind_estimate(draft_estimate))
        self.assertFalse(invoice_model.can_bind_estimate(review_estimate))

        with self.assertRaises(InvoiceModelValidationError):
            invoice_model.bind_estimate(draft_estimate, commit=True)

        with self.assertRaises(InvoiceModelValidationError):
            invoice_model.bind_estimate(review_estimate, commit=True)

        invoice_model.refresh_from_db()
        self.assertIsNone(invoice_model.ce_model_id)

    def test_binding_updates_invoice_customer_from_estimate(self):
        setup = self.create_entity_setup(name="API Estimate Invoice Binding Customer Entity")
        estimate_model = self.make_approved_estimate(setup)
        invoice_model = self.create_invoice(setup, customer_model=setup["other_customer_model"])

        self.assertNotEqual(invoice_model.customer_id, estimate_model.customer_id)

        invoice_model.bind_estimate(estimate_model, commit=True)
        invoice_model.refresh_from_db()

        self.assertEqual(invoice_model.ce_model_id, estimate_model.uuid)
        self.assertEqual(invoice_model.customer_id, estimate_model.customer_id)

    def test_already_bound_invoice_rejects_second_estimate(self):
        setup = self.create_entity_setup(name="API Estimate Invoice Binding Bound Entity")
        first_estimate = self.make_approved_estimate(setup, title="API First Estimate")
        second_estimate = self.make_approved_estimate(setup, title="API Second Estimate")
        invoice_model = self.create_invoice(setup)
        invoice_model.bind_estimate(first_estimate, commit=True)
        invoice_model.refresh_from_db()

        self.assertFalse(invoice_model.can_bind_estimate(second_estimate))

        with self.assertRaises(InvoiceModelValidationError):
            invoice_model.bind_estimate(second_estimate, commit=True)

        invoice_model.refresh_from_db()
        self.assertEqual(invoice_model.ce_model_id, first_estimate.uuid)

    def test_cross_entity_estimate_cannot_bind_to_invoice(self):
        setup = self.create_entity_setup(name="API Estimate Invoice Binding Entity A")
        other_setup = self.create_entity_setup(name="API Estimate Invoice Binding Entity B")
        other_estimate = self.make_approved_estimate(other_setup)
        invoice_model = self.create_invoice(setup)

        self.assertFalse(invoice_model.can_bind_estimate(other_estimate))

        with self.assertRaises(InvoiceModelValidationError):
            invoice_model.bind_estimate(other_estimate, commit=True)

        invoice_model.refresh_from_db()
        self.assertIsNone(invoice_model.ce_model_id)
        self.assertEqual(invoice_model.entity_model_id, setup["entity_model"].uuid)
        self.assertEqual(invoice_model.customer_id, setup["customer_model"].uuid)
