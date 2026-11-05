"""
High-level API tests for BillModel configuration and itemization behavior.
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
    ASSET_CA_PREPAID,
    COGS,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
)
from django_ledger.models import BillModel, ItemTransactionModel
from django_ledger.models.bill import BillModelValidationError
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.vendor import VendorModel


class BillConfigureItemizationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_bill_configure_user",
            email="api-bill-configure-user@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_bill_configure_unrelated",
            email="api-bill-configure-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(
        self,
        *,
        name="API Bill Configure Entity",
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
        prepaid_account = coa_model.create_account(
            code="1310",
            name=f"{name} Prepaid Account",
            role=ASSET_CA_PREPAID,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        payable_account = coa_model.create_account(
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
            unit_abbr=f"{name[:8].lower().replace(' ', '-')}-u",
            active=True,
            commit=True,
        )
        vendor_model = VendorModel(
            vendor_name=f"{name} Vendor",
            entity_model=entity_model,
            description=f"{name} Vendor description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()
        expense_item = entity_model.create_item_expense(
            name=f"{name} Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        inventory_item = entity_model.create_item_inventory(
            name=f"{name} Inventory Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=inventory_account,
            coa_model=coa_model,
            commit=True,
        )
        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "prepaid_account": prepaid_account,
            "payable_account": payable_account,
            "expense_account": expense_account,
            "vendor_model": vendor_model,
            "expense_item": expense_item,
            "inventory_item": inventory_item,
            "service_item": service_item,
        }

    def build_bill(self, setup, **overrides):
        bill_kwargs = {
            "vendor": setup["vendor_model"],
            "terms": BillModel.TERMS_NET_30,
            "cash_account": setup["cash_account"],
            "prepaid_account": setup["prepaid_account"],
            "unearned_account": setup["payable_account"],
        }
        bill_kwargs.update(overrides)
        return BillModel(**bill_kwargs)

    def configure_bill(
        self,
        setup,
        *,
        entity_input=None,
        user_model=None,
        commit=True,
        commit_ledger=False,
        **bill_overrides,
    ):
        bill_model = self.build_bill(setup, **bill_overrides)
        _ledger_model, bill_model = bill_model.configure(
            entity_slug=setup["entity_model"] if entity_input is None else entity_input,
            user_model=self.user if user_model is None else user_model,
            date_draft=date(2026, 1, 15),
            ledger_name="API Bill Configure Ledger",
            commit=commit,
            commit_ledger=commit_ledger,
        )
        if commit:
            bill_model.refresh_from_db()
        return bill_model

    def migrate_expense_item(self, bill_model, setup, *, quantity="2.00", unit_cost="50.00", operation=None):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        itemtxs = {
            setup["expense_item"].item_number: {
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_amount": quantity * unit_cost,
            }
        }
        itemtxs_batch = bill_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=operation or BillModel.ITEMIZE_REPLACE,
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model, itemtxs_batch

    def test_configure_accepts_entity_model_and_authorized_slug(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]

        by_model = self.configure_bill(setup, entity_input=entity_model)
        by_slug = self.configure_bill(setup, entity_input=entity_model.slug)

        self.assertEqual(by_model.entity_model_id, entity_model.uuid)
        self.assertEqual(by_slug.entity_model_id, entity_model.uuid)
        self.assertEqual(by_model.vendor_id, setup["vendor_model"].uuid)
        self.assertEqual(by_slug.vendor_id, setup["vendor_model"].uuid)
        self.assertTrue(by_model.bill_number)
        self.assertTrue(by_slug.bill_number)

    def test_configure_rejects_uuid_entity_input_and_unauthorized_slug(self):
        setup = self.create_entity_setup(name="API Bill Configure Rejection Entity")

        with self.assertRaises(BillModelValidationError):
            self.configure_bill(setup, entity_input=setup["entity_model"].uuid)

        with self.assertRaises(BillModelValidationError):
            self.build_bill(setup).configure(entity_slug=setup["entity_model"].slug)

        with self.assertRaises(Http404):
            self.configure_bill(setup, entity_input=setup["entity_model"].slug, user_model=self.unrelated_user)

    def test_configure_commit_false_persists_wrapper_ledger_but_not_bill(self):
        setup = self.create_entity_setup(name="API Bill Configure Commit False Entity")

        bill_model = self.configure_bill(setup, commit=False, commit_ledger=False)

        self.assertTrue(bill_model.is_configured())
        self.assertTrue(bill_model.bill_number)
        self.assertIsNotNone(bill_model.ledger_id)
        self.assertFalse(BillModel.objects.filter(uuid=bill_model.uuid).exists())
        self.assertTrue(bill_model.ledger.__class__.objects.filter(uuid=bill_model.ledger_id).exists())
        self.assertTrue(bill_model.ledger.ledger_xid)

    def test_configure_commit_ledger_true_persists_ledger_without_persisting_bill(self):
        setup = self.create_entity_setup(name="API Bill Configure Ledger Commit Entity")

        bill_model = self.configure_bill(setup, commit=False, commit_ledger=True)

        self.assertFalse(BillModel.objects.filter(uuid=bill_model.uuid).exists())
        self.assertTrue(bill_model.ledger.__class__.objects.filter(uuid=bill_model.ledger_id).exists())

    def test_configure_sets_accrual_behavior_from_entity_accounting_method(self):
        accrual_setup = self.create_entity_setup(name="API Bill Configure Accrual Entity", use_accrual_method=True)
        cash_setup = self.create_entity_setup(name="API Bill Configure Cash Entity", use_accrual_method=False)

        accrual_bill = self.configure_bill(accrual_setup)
        cash_bill = self.configure_bill(cash_setup)

        self.assertTrue(accrual_bill.accrue)
        self.assertEqual(accrual_bill.progress, Decimal("1.00"))
        self.assertFalse(cash_bill.accrue)

    def test_clean_rejects_invalid_account_roles(self):
        setup = self.create_entity_setup(name="API Bill Configure Invalid Role Entity")

        with self.assertRaises(ValidationError):
            self.configure_bill(setup, cash_account=setup["expense_account"])

        with self.assertRaises(ValidationError):
            self.configure_bill(setup, prepaid_account=setup["cash_account"])

        with self.assertRaises(ValidationError):
            self.configure_bill(setup, unearned_account=setup["cash_account"])

    def test_get_item_model_qs_returns_bill_eligible_items(self):
        setup = self.create_entity_setup(name="API Bill Configure Item Query Entity")
        bill_model = self.configure_bill(setup)

        item_qs = bill_model.get_item_model_qs()

        self.assertTrue(item_qs.filter(uuid=setup["expense_item"].uuid).exists())
        self.assertTrue(item_qs.filter(uuid=setup["inventory_item"].uuid).exists())
        self.assertFalse(item_qs.filter(uuid=setup["service_item"].uuid).exists())

    def test_migrate_itemtxs_replace_creates_bill_items_and_updates_amount_due(self):
        setup = self.create_entity_setup(name="API Bill Configure Item Migration Entity")
        bill_model = self.configure_bill(setup)

        bill_model, itemtxs_batch = self.migrate_expense_item(bill_model, setup)

        self.assertEqual(len(itemtxs_batch), 1)
        item_tx = ItemTransactionModel.objects.get(bill_model=bill_model)
        self.assertEqual(item_tx.item_model_id, setup["expense_item"].uuid)
        self.assertEqual(item_tx.quantity, Decimal("2.00"))
        self.assertEqual(item_tx.unit_cost, Decimal("50.00"))
        self.assertEqual(item_tx.total_amount, Decimal("100.00"))
        self.assertEqual(bill_model.amount_due, Decimal("100.00"))

        bill_model, replacement_batch = self.migrate_expense_item(
            bill_model,
            setup,
            quantity="1.00",
            unit_cost="25.00",
        )
        self.assertEqual(len(replacement_batch), 1)
        self.assertEqual(ItemTransactionModel.objects.filter(bill_model=bill_model).count(), 1)
        self.assertEqual(bill_model.amount_due, Decimal("25.00"))

    def test_validate_itemtxs_qs_rejects_transactions_from_another_bill(self):
        setup = self.create_entity_setup(name="API Bill Configure Validate ItemTx Entity")
        bill_model = self.configure_bill(setup)
        other_bill_model = self.configure_bill(setup)
        other_bill_model, _itemtxs_batch = self.migrate_expense_item(other_bill_model, setup)
        other_itemtxs = list(ItemTransactionModel.objects.filter(bill_model=other_bill_model))

        with self.assertRaises(BillModelValidationError):
            bill_model.validate_itemtxs_qs(other_itemtxs)

    def test_get_itemtxs_data_and_update_amount_due_use_item_transaction_totals(self):
        setup = self.create_entity_setup(name="API Bill Configure Item Data Entity")
        bill_model = self.configure_bill(setup)
        bill_model, _itemtxs_batch = self.migrate_expense_item(bill_model, setup)

        itemtxs_qs, itemtxs_data = bill_model.get_itemtxs_data()

        self.assertEqual(itemtxs_qs.count(), 1)
        self.assertEqual(itemtxs_data["total_amount__sum"], Decimal("100.00"))
        self.assertEqual(itemtxs_data["total_items"], 1)

        bill_model.amount_due = Decimal("0.00")
        bill_model.update_amount_due(itemtxs_qs=itemtxs_qs)

        self.assertEqual(bill_model.amount_due, Decimal("100.00"))
