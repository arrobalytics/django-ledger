"""
High-level API behavior tests for UnitOfMeasureModel and ItemModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import AccountModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel, UnitOfMeasureModel


class ItemHighLevelAPITest(TestCase):
    """
    High-level behavior tests for UnitOfMeasureModel and ItemModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic item/catalog API invariants that
    should remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_item_contract_user",
            email="api-item-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_with_accounting_setup(self, *, name="API Item Contract Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Item Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        cash_account = coa_model.create_account(
            code="1010",
            name="API Item Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        inventory_account = coa_model.create_account(
            code="1510",
            name="API Item Inventory Account",
            role="asset_ca_inv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        cogs_account = coa_model.create_account(
            code="5010",
            name="API Item COGS Account",
            role="cogs_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        earnings_account = coa_model.create_account(
            code="4010",
            name="API Item Earnings Account",
            role="in_operational",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        expense_account = coa_model.create_account(
            code="6010",
            name="API Item Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "inventory_account": inventory_account,
            "cogs_account": cogs_account,
            "earnings_account": earnings_account,
            "expense_account": expense_account,
        }

    def create_uom(self, entity_model, *, name="API Unit", unit_abbr="api-unit"):
        return entity_model.create_uom(
            name=name,
            unit_abbr=unit_abbr,
            active=True,
            commit=True,
        )

    def test_create_uom_creates_unit_under_entity_context(self):
        setup = self.create_entity_with_accounting_setup()
        entity_model = setup["entity_model"]

        uom_model = self.create_uom(
            entity_model,
            name="API Hour",
            unit_abbr="api-hour",
        )

        self.assertIsInstance(uom_model, UnitOfMeasureModel)
        self.assertIsNotNone(uom_model.uuid)
        self.assertEqual(uom_model.entity_id, entity_model.uuid)
        self.assertEqual(uom_model.name, "API Hour")
        self.assertEqual(uom_model.unit_abbr, "api-hour")
        self.assertTrue(uom_model.is_active)

    def test_create_expense_item_assigns_expense_role_and_account(self):
        setup = self.create_entity_with_accounting_setup()
        entity_model = setup["entity_model"]
        expense_account = setup["expense_account"]
        uom_model = self.create_uom(entity_model)

        item_model = entity_model.create_item_expense(
            name="API Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            commit=True,
        )

        self.assertIsInstance(item_model, ItemModel)
        self.assertEqual(item_model.entity_id, entity_model.uuid)
        self.assertEqual(item_model.name, "API Expense Item")
        self.assertTrue(item_model.is_expense())
        self.assertEqual(item_model.expense_account_id, expense_account.uuid)
        self.assertEqual(item_model.uom_id, uom_model.uuid)
        self.assertTrue(item_model.item_number)

    def test_create_service_item_assigns_service_role_and_accounts(self):
        setup = self.create_entity_with_accounting_setup()
        entity_model = setup["entity_model"]
        uom_model = self.create_uom(entity_model)

        item_model = entity_model.create_item_service(
            name="API Service Item",
            uom_model=uom_model,
            coa_model=setup["coa_model"],
            commit=True,
        )

        self.assertIsInstance(item_model, ItemModel)
        self.assertEqual(item_model.entity_id, entity_model.uuid)
        self.assertEqual(item_model.name, "API Service Item")
        self.assertTrue(item_model.is_service())
        self.assertEqual(item_model.uom_id, uom_model.uuid)
        self.assertIsNotNone(item_model.cogs_account_id)
        self.assertIsNotNone(item_model.earnings_account_id)
        self.assertTrue(item_model.item_number)

    def test_create_product_item_assigns_product_role_and_accounts(self):
        setup = self.create_entity_with_accounting_setup()
        entity_model = setup["entity_model"]
        uom_model = self.create_uom(entity_model)

        item_model = entity_model.create_item_product(
            name="API Product Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            coa_model=setup["coa_model"],
            commit=True,
        )

        self.assertIsInstance(item_model, ItemModel)
        self.assertEqual(item_model.entity_id, entity_model.uuid)
        self.assertEqual(item_model.name, "API Product Item")
        self.assertTrue(item_model.is_product())
        self.assertEqual(item_model.uom_id, uom_model.uuid)
        self.assertIsNotNone(item_model.inventory_account_id)
        self.assertIsNotNone(item_model.cogs_account_id)
        self.assertIsNotNone(item_model.earnings_account_id)
        self.assertTrue(item_model.item_number)

    def test_create_inventory_item_assigns_inventory_role_and_account(self):
        setup = self.create_entity_with_accounting_setup()
        entity_model = setup["entity_model"]
        inventory_account = setup["inventory_account"]
        uom_model = self.create_uom(entity_model)

        item_model = entity_model.create_item_inventory(
            name="API Inventory Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=inventory_account,
            coa_model=setup["coa_model"],
            commit=True,
        )

        self.assertIsInstance(item_model, ItemModel)
        self.assertEqual(item_model.entity_id, entity_model.uuid)
        self.assertEqual(item_model.name, "API Inventory Item")
        self.assertTrue(item_model.is_inventory())
        self.assertEqual(item_model.inventory_account_id, inventory_account.uuid)
        self.assertEqual(item_model.uom_id, uom_model.uuid)
        self.assertTrue(item_model.item_number)

    def test_item_for_entity_limits_queryset_to_entity_scope(self):
        setup = self.create_entity_with_accounting_setup(name="API Item Entity A")
        other_setup = self.create_entity_with_accounting_setup(name="API Item Entity B")

        uom_model = self.create_uom(setup["entity_model"], unit_abbr="api-unit-a")
        other_uom_model = self.create_uom(other_setup["entity_model"], unit_abbr="api-unit-b")

        item_model = setup["entity_model"].create_item_expense(
            name="API Entity A Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=setup["expense_account"],
            commit=True,
        )

        other_item_model = other_setup["entity_model"].create_item_expense(
            name="API Entity B Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=other_uom_model,
            expense_account=other_setup["expense_account"],
            commit=True,
        )

        scoped_qs = ItemModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(scoped_qs.filter(uuid=item_model.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_item_model.uuid).exists())

    def test_item_invoice_queryset_exposes_product_and_service_items(self):
        setup = self.create_entity_with_accounting_setup()
        entity_model = setup["entity_model"]
        uom_model = self.create_uom(entity_model)

        product_item = entity_model.create_item_product(
            name="API Invoice Product Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            coa_model=setup["coa_model"],
            commit=True,
        )

        service_item = entity_model.create_item_service(
            name="API Invoice Service Item",
            uom_model=uom_model,
            coa_model=setup["coa_model"],
            commit=True,
        )

        expense_item = entity_model.create_item_expense(
            name="API Invoice Excluded Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=setup["expense_account"],
            commit=True,
        )

        invoice_items_qs = ItemModel.objects.for_invoice(entity_model)

        self.assertTrue(invoice_items_qs.filter(uuid=product_item.uuid).exists())
        self.assertTrue(invoice_items_qs.filter(uuid=service_item.uuid).exists())
        self.assertFalse(invoice_items_qs.filter(uuid=expense_item.uuid).exists())

    def test_item_bill_queryset_exposes_expense_and_inventory_items(self):
        setup = self.create_entity_with_accounting_setup()
        entity_model = setup["entity_model"]
        uom_model = self.create_uom(entity_model)

        expense_item = entity_model.create_item_expense(
            name="API Bill Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=setup["expense_account"],
            commit=True,
        )

        inventory_item = entity_model.create_item_inventory(
            name="API Bill Inventory Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=setup["inventory_account"],
            coa_model=setup["coa_model"],
            commit=True,
        )

        service_item = entity_model.create_item_service(
            name="API Bill Excluded Service Item",
            uom_model=uom_model,
            coa_model=setup["coa_model"],
            commit=True,
        )

        bill_items_qs = ItemModel.objects.for_bill(entity_model)

        self.assertTrue(bill_items_qs.filter(uuid=expense_item.uuid).exists())
        self.assertTrue(bill_items_qs.filter(uuid=inventory_item.uuid).exists())
        self.assertFalse(bill_items_qs.filter(uuid=service_item.uuid).exists())
