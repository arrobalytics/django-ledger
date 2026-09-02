"""
High-level API tests for InvoiceModel configuration and itemization behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import Http404
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_INVENTORY,
    ASSET_CA_RECEIVABLES,
    COGS,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
    LIABILITY_CL_DEFERRED_REVENUE,
)
from django_ledger.models import InvoiceModel, ItemTransactionModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModelValidationError
from django_ledger.models.items import ItemModel


class InvoiceConfigureItemizationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_invoice_configure_user",
            email="api-invoice-configure-user@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_invoice_configure_unrelated",
            email="api-invoice-configure-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(
        self,
        *,
        name="API Invoice Configure Entity",
        use_accrual_method=True,
    ):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=use_accrual_method,
            fy_start_month=1,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        cash_account = coa_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role=ASSET_CA_CASH,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        receivable_account = coa_model.create_account(
            code="1210",
            name=f"{name} Receivable Account",
            role=ASSET_CA_RECEIVABLES,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        deferred_account = coa_model.create_account(
            code="2310",
            name=f"{name} Deferred Revenue Account",
            role=LIABILITY_CL_DEFERRED_REVENUE,
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
        cogs_account = coa_model.create_account(
            code="5010",
            name=f"{name} COGS Account",
            role=COGS,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        inventory_account = coa_model.create_account(
            code="1410",
            name=f"{name} Inventory Account",
            role=ASSET_CA_INVENTORY,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        income_account = coa_model.create_account(
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
            description=f"{name} Customer description",
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
        product_item = entity_model.create_item_product(
            name=f"{name} Product Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            coa_model=coa_model,
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
            "coa_model": coa_model,
            "cash_account": cash_account,
            "receivable_account": receivable_account,
            "deferred_account": deferred_account,
            "expense_account": expense_account,
            "cogs_account": cogs_account,
            "inventory_account": inventory_account,
            "income_account": income_account,
            "customer_model": customer_model,
            "service_item": service_item,
            "product_item": product_item,
            "expense_item": expense_item,
        }

    def build_invoice(self, setup, **overrides):
        invoice_kwargs = {
            "customer": setup["customer_model"],
            "terms": InvoiceModel.TERMS_NET_30,
            "cash_account": setup["cash_account"],
            "prepaid_account": setup["receivable_account"],
            "unearned_account": setup["deferred_account"],
        }
        invoice_kwargs.update(overrides)
        return InvoiceModel(**invoice_kwargs)

    def configure_invoice(
        self,
        setup,
        *,
        entity_input=None,
        user_model=None,
        commit=True,
        commit_ledger=False,
        **invoice_overrides,
    ):
        invoice_model = self.build_invoice(setup, **invoice_overrides)
        _ledger_model, invoice_model = invoice_model.configure(
            entity_slug=setup["entity_model"] if entity_input is None else entity_input,
            user_model=self.user if user_model is None else user_model,
            date_draft=date(2026, 1, 15),
            ledger_name="API Invoice Configure Ledger",
            commit=commit,
            commit_ledger=commit_ledger,
        )
        if commit:
            invoice_model.refresh_from_db()
        return invoice_model

    def migrate_service_item(self, invoice_model, setup, *, quantity="2.00", unit_cost="50.00", operation=None):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        itemtxs = {
            setup["service_item"].item_number: {
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_amount": quantity * unit_cost,
            }
        }
        itemtxs_batch = invoice_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=operation or InvoiceModel.ITEMIZE_REPLACE,
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model, itemtxs_batch

    def test_configure_accepts_entity_model_and_authorized_slug(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]

        by_model = self.configure_invoice(setup, entity_input=entity_model)
        by_slug = self.configure_invoice(setup, entity_input=entity_model.slug)

        self.assertEqual(by_model.entity_model_id, entity_model.uuid)
        self.assertEqual(by_slug.entity_model_id, entity_model.uuid)
        self.assertEqual(by_model.customer_id, setup["customer_model"].uuid)
        self.assertEqual(by_slug.customer_id, setup["customer_model"].uuid)
        self.assertTrue(by_model.invoice_number)
        self.assertTrue(by_slug.invoice_number)

    def test_configure_rejects_uuid_entity_input_and_unauthorized_slug(self):
        setup = self.create_entity_setup(name="API Invoice Configure Rejection Entity")

        with self.assertRaises(InvoiceModelValidationError):
            self.configure_invoice(setup, entity_input=setup["entity_model"].uuid)

        with self.assertRaises(InvoiceModelValidationError):
            self.build_invoice(setup).configure(entity_slug=setup["entity_model"].slug)

        with self.assertRaises(Http404):
            self.configure_invoice(setup, entity_input=setup["entity_model"].slug, user_model=self.unrelated_user)

    def test_configure_commit_false_persists_wrapper_ledger_but_not_invoice(self):
        setup = self.create_entity_setup(name="API Invoice Configure Commit False Entity")

        invoice_model = self.configure_invoice(setup, commit=False, commit_ledger=False)

        self.assertTrue(invoice_model.is_configured())
        self.assertTrue(invoice_model.invoice_number)
        self.assertIsNotNone(invoice_model.ledger_id)
        self.assertFalse(InvoiceModel.objects.filter(uuid=invoice_model.uuid).exists())
        self.assertTrue(invoice_model.ledger.__class__.objects.filter(uuid=invoice_model.ledger_id).exists())
        self.assertTrue(invoice_model.ledger.ledger_xid)

    def test_configure_commit_ledger_true_persists_ledger_without_persisting_invoice(self):
        setup = self.create_entity_setup(name="API Invoice Configure Ledger Commit Entity")

        invoice_model = self.configure_invoice(setup, commit=False, commit_ledger=True)

        self.assertFalse(InvoiceModel.objects.filter(uuid=invoice_model.uuid).exists())
        self.assertTrue(invoice_model.ledger.__class__.objects.filter(uuid=invoice_model.ledger_id).exists())

    def test_configure_sets_accrual_behavior_from_entity_accounting_method(self):
        accrual_setup = self.create_entity_setup(name="API Invoice Configure Accrual Entity", use_accrual_method=True)
        cash_setup = self.create_entity_setup(name="API Invoice Configure Cash Entity", use_accrual_method=False)

        accrual_invoice = self.configure_invoice(accrual_setup)
        cash_invoice = self.configure_invoice(cash_setup)

        self.assertTrue(accrual_invoice.accrue)
        self.assertEqual(accrual_invoice.progress, Decimal("1.00"))
        self.assertFalse(cash_invoice.accrue)

    def test_clean_rejects_invalid_account_roles(self):
        setup = self.create_entity_setup(name="API Invoice Configure Invalid Role Entity")

        with self.assertRaises(ValidationError):
            self.configure_invoice(setup, cash_account=setup["expense_account"])

        with self.assertRaises(ValidationError):
            self.configure_invoice(setup, prepaid_account=setup["cash_account"])

        with self.assertRaises(ValidationError):
            self.configure_invoice(setup, unearned_account=setup["cash_account"])

    def test_get_item_model_qs_returns_invoice_eligible_items(self):
        setup = self.create_entity_setup(name="API Invoice Configure Item Query Entity")
        invoice_model = self.configure_invoice(setup)

        item_qs = invoice_model.get_item_model_qs()

        self.assertTrue(item_qs.filter(uuid=setup["service_item"].uuid).exists())
        self.assertTrue(item_qs.filter(uuid=setup["product_item"].uuid).exists())
        self.assertFalse(item_qs.filter(uuid=setup["expense_item"].uuid).exists())

    def test_migrate_itemtxs_replace_creates_invoice_items_and_updates_amount_due(self):
        setup = self.create_entity_setup(name="API Invoice Configure Item Migration Entity")
        invoice_model = self.configure_invoice(setup)

        invoice_model, itemtxs_batch = self.migrate_service_item(invoice_model, setup)

        self.assertEqual(len(itemtxs_batch), 1)
        item_tx = ItemTransactionModel.objects.get(invoice_model=invoice_model)
        self.assertEqual(item_tx.item_model_id, setup["service_item"].uuid)
        self.assertEqual(item_tx.quantity, Decimal("2.00"))
        self.assertEqual(item_tx.unit_cost, Decimal("50.00"))
        self.assertEqual(item_tx.total_amount, Decimal("100.00"))
        self.assertEqual(invoice_model.amount_due, Decimal("100.00"))

        invoice_model, replacement_batch = self.migrate_service_item(
            invoice_model,
            setup,
            quantity="1.00",
            unit_cost="25.00",
        )
        self.assertEqual(len(replacement_batch), 1)
        self.assertEqual(ItemTransactionModel.objects.filter(invoice_model=invoice_model).count(), 1)
        self.assertEqual(invoice_model.amount_due, Decimal("25.00"))

    def test_validate_itemtxs_qs_rejects_transactions_from_another_invoice(self):
        setup = self.create_entity_setup(name="API Invoice Configure Validate ItemTx Entity")
        invoice_model = self.configure_invoice(setup)
        other_invoice_model = self.configure_invoice(setup)
        other_invoice_model, _itemtxs_batch = self.migrate_service_item(other_invoice_model, setup)
        other_itemtxs = list(ItemTransactionModel.objects.filter(invoice_model=other_invoice_model))

        with self.assertRaises(InvoiceModelValidationError):
            invoice_model.validate_itemtxs_qs(other_itemtxs)

    def test_get_itemtxs_data_and_update_amount_due_use_item_transaction_totals(self):
        setup = self.create_entity_setup(name="API Invoice Configure Item Data Entity")
        invoice_model = self.configure_invoice(setup)
        invoice_model, _itemtxs_batch = self.migrate_service_item(invoice_model, setup)

        itemtxs_qs, itemtxs_data = invoice_model.get_itemtxs_data()

        self.assertEqual(itemtxs_qs.count(), 1)
        self.assertEqual(itemtxs_data["total_amount__sum"], Decimal("100.00"))
        self.assertEqual(itemtxs_data["total_items"], 1)

        invoice_model.amount_due = Decimal("0.00")
        invoice_model.update_amount_due(itemtxs_qs=itemtxs_qs)

        self.assertEqual(invoice_model.amount_due, Decimal("100.00"))
