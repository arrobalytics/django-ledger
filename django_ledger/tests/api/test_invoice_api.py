"""
High-level API behavior tests for InvoiceModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import InvoiceModel, ItemTransactionModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel


class InvoiceHighLevelAPITest(TestCase):
    """
    High-level behavior tests for InvoiceModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic invoice/customer/item lifecycle
    invariants that should remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_invoice_contract_user",
            email="api-invoice-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_with_invoice_setup(self, *, name="API Invoice Contract Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Invoice Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        cash_account = coa_model.create_account(
            code="1010",
            name="API Invoice Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        receivable_account = coa_model.create_account(
            code="1210",
            name="API Invoice Receivable Account",
            role="asset_ca_recv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        unearned_account = coa_model.create_account(
            code="2310",
            name="API Invoice Unearned Revenue Account",
            role="lia_cl_def_rev",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        inventory_account = coa_model.create_account(
            code="1510",
            name="API Invoice Inventory Account",
            role="asset_ca_inv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        cogs_account = coa_model.create_account(
            code="5010",
            name="API Invoice COGS Account",
            role="cogs_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        earnings_account = coa_model.create_account(
            code="4010",
            name="API Invoice Earnings Account",
            role="in_operational",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        uom_model = entity_model.create_uom(
            name="API Invoice Unit",
            unit_abbr="api-inv",
            active=True,
            commit=True,
        )

        customer_model = CustomerModel(
            customer_name="API Invoice Customer",
            entity_model=entity_model,
            description="API Invoice Customer description",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()

        service_item = entity_model.create_item_service(
            name="API Invoice Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )

        product_item = entity_model.create_item_product(
            name="API Invoice Product Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "receivable_account": receivable_account,
            "unearned_account": unearned_account,
            "inventory_account": inventory_account,
            "cogs_account": cogs_account,
            "earnings_account": earnings_account,
            "uom_model": uom_model,
            "customer_model": customer_model,
            "service_item": service_item,
            "product_item": product_item,
        }

    def create_configured_invoice(self, setup):
        invoice_model = InvoiceModel(
            customer=setup["customer_model"],
            cash_account=setup["cash_account"],
            prepaid_account=setup["receivable_account"],
            unearned_account=setup["unearned_account"],
        )

        _ledger_model, invoice_model = invoice_model.configure(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            date_draft=date(2026, 1, 15),
            commit=True,
        )

        return invoice_model

    def migrate_service_item(self, invoice_model, setup, *, quantity="2.00", unit_cost="50.00"):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)

        itemtxs = {
            setup["service_item"].item_number: {
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_amount": quantity * unit_cost,
            }
        }

        invoice_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=InvoiceModel.ITEMIZE_REPLACE,
            commit=True,
        )

        invoice_model.refresh_from_db()
        return invoice_model

    def test_invoice_configure_creates_draft_invoice_under_entity_and_customer(self):
        setup = self.create_entity_with_invoice_setup()

        invoice_model = self.create_configured_invoice(setup)

        self.assertIsInstance(invoice_model, InvoiceModel)
        self.assertIsNotNone(invoice_model.uuid)
        self.assertEqual(invoice_model.ledger.entity_id, setup["entity_model"].uuid)
        self.assertEqual(invoice_model.customer_id, setup["customer_model"].uuid)
        self.assertTrue(invoice_model.is_draft())
        self.assertFalse(invoice_model.is_approved())
        self.assertFalse(invoice_model.is_paid())
        self.assertTrue(invoice_model.invoice_number)

    def test_invoice_item_migration_creates_item_transaction(self):
        setup = self.create_entity_with_invoice_setup()
        invoice_model = self.create_configured_invoice(setup)

        self.migrate_service_item(invoice_model, setup)

        item_txs = ItemTransactionModel.objects.filter(invoice_model=invoice_model)

        self.assertEqual(item_txs.count(), 1)

        item_tx = item_txs.get()

        self.assertEqual(item_tx.item_model_id, setup["service_item"].uuid)
        self.assertEqual(item_tx.quantity, Decimal("2.00"))
        self.assertEqual(item_tx.unit_cost, Decimal("50.00"))
        self.assertEqual(item_tx.total_amount, Decimal("100.00"))

    def test_invoice_item_migration_updates_amount_due(self):
        setup = self.create_entity_with_invoice_setup()
        invoice_model = self.create_configured_invoice(setup)

        invoice_model = self.migrate_service_item(invoice_model, setup)

        self.assertEqual(invoice_model.amount_due, Decimal("100.00"))
        self.assertEqual(invoice_model.amount_paid, Decimal("0.00"))

    def test_invoice_for_entity_queryset_limits_scope(self):
        setup = self.create_entity_with_invoice_setup(name="API Invoice Entity A")
        other_setup = self.create_entity_with_invoice_setup(name="API Invoice Entity B")

        invoice_model = self.create_configured_invoice(setup)
        other_invoice_model = self.create_configured_invoice(other_setup)

        scoped_qs = InvoiceModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(scoped_qs.filter(uuid=invoice_model.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_invoice_model.uuid).exists())

    def test_invoice_can_move_from_draft_to_review(self):
        setup = self.create_entity_with_invoice_setup()
        invoice_model = self.create_configured_invoice(setup)
        invoice_model = self.migrate_service_item(invoice_model, setup)

        invoice_model.mark_as_review(commit=True)
        invoice_model.refresh_from_db()

        self.assertTrue(invoice_model.is_review())
        self.assertFalse(invoice_model.is_draft())

    def test_invoice_can_move_from_review_to_approved(self):
        setup = self.create_entity_with_invoice_setup()
        invoice_model = self.create_configured_invoice(setup)
        invoice_model = self.migrate_service_item(invoice_model, setup)

        invoice_model.mark_as_review(commit=True)
        invoice_model.refresh_from_db()

        invoice_model.mark_as_approved(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        invoice_model.refresh_from_db()

        self.assertTrue(invoice_model.is_approved())
        self.assertFalse(invoice_model.is_paid())
        self.assertEqual(invoice_model.amount_due, Decimal("100.00"))

    def test_approved_invoice_can_be_marked_paid(self):
        setup = self.create_entity_with_invoice_setup()
        invoice_model = self.create_configured_invoice(setup)
        invoice_model = self.migrate_service_item(invoice_model, setup)

        invoice_model.mark_as_review(commit=True)
        invoice_model.refresh_from_db()

        invoice_model.mark_as_approved(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        invoice_model.refresh_from_db()

        invoice_model.mark_as_paid(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        invoice_model.refresh_from_db()

        self.assertTrue(invoice_model.is_paid())
        self.assertEqual(invoice_model.amount_paid, invoice_model.amount_due)
