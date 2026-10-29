"""
High-level API tests for ItemModel role, account, and numbering behavior.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_INVENTORY,
    COGS,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
)
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel, ItemModelValidationError
from django_ledger.settings import (
    DJANGO_LEDGER_EXPENSE_NUMBER_PREFIX,
    DJANGO_LEDGER_INVENTORY_NUMBER_PREFIX,
    DJANGO_LEDGER_PRODUCT_NUMBER_PREFIX,
)


class ItemRoleAccountAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_item_role_account_admin",
            email="api-item-role-account-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Item Role Account Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        inventory_account = coa_model.create_account(
            code="1510",
            name=f"{name} Inventory Account",
            role=ASSET_CA_INVENTORY,
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
        earnings_account = coa_model.create_account(
            code="4010",
            name=f"{name} Income Account",
            role=INCOME_OPERATIONAL,
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
            unit_abbr=f"ir-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "inventory_account": inventory_account,
            "cogs_account": cogs_account,
            "earnings_account": earnings_account,
            "expense_account": expense_account,
            "uom_model": uom_model,
        }

    def create_items(self, setup, *, name_prefix="API Item Role Account"):
        entity_model = setup["entity_model"]
        uom_model = setup["uom_model"]
        return {
            "product": entity_model.create_item_product(
                name=f"{name_prefix} Product",
                item_type=ItemModel.ITEM_TYPE_MATERIAL,
                uom_model=uom_model,
                coa_model=setup["coa_model"],
                commit=True,
            ),
            "service": entity_model.create_item_service(
                name=f"{name_prefix} Service",
                uom_model=uom_model,
                coa_model=setup["coa_model"],
                commit=True,
            ),
            "expense": entity_model.create_item_expense(
                name=f"{name_prefix} Expense",
                expense_type=ItemModel.ITEM_TYPE_OTHER,
                uom_model=uom_model,
                expense_account=setup["expense_account"],
                commit=True,
            ),
            "inventory": entity_model.create_item_inventory(
                name=f"{name_prefix} Inventory",
                item_type=ItemModel.ITEM_TYPE_MATERIAL,
                uom_model=uom_model,
                inventory_account=setup["inventory_account"],
                coa_model=setup["coa_model"],
                commit=True,
            ),
        }

    def make_item(self, setup, *, item_role, item_type=ItemModel.ITEM_TYPE_MATERIAL, **accounts):
        return ItemModel(
            entity=setup["entity_model"],
            name=f"API Direct {item_role.title()} Item",
            uom=setup["uom_model"],
            item_role=item_role,
            item_type=item_type,
            **accounts,
        )

    def item_sequence(self, item_model):
        return int(item_model.item_number.rsplit("-", 1)[-1])

    def test_role_helpers_identify_representative_item_roles(self):
        items = self.create_items(self.create_entity_setup())

        self.assertTrue(items["product"].is_product())
        self.assertFalse(items["product"].is_service())
        self.assertTrue(items["service"].is_service())
        self.assertFalse(items["service"].is_product())
        self.assertTrue(items["expense"].is_expense())
        self.assertFalse(items["expense"].is_inventory())
        self.assertTrue(items["inventory"].is_inventory())
        self.assertFalse(items["inventory"].is_expense())

    def test_type_helpers_identify_representative_item_types(self):
        setup = self.create_entity_setup()

        labor_item = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_SERVICE,
            item_type=ItemModel.ITEM_TYPE_LABOR,
        )
        material_item = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_PRODUCT,
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
        )
        equipment_item = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_PRODUCT,
            item_type=ItemModel.ITEM_TYPE_EQUIPMENT,
        )
        lump_sum_item = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_EXPENSE,
            item_type=ItemModel.ITEM_TYPE_LUMP_SUM,
        )
        other_item = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_EXPENSE,
            item_type=ItemModel.ITEM_TYPE_OTHER,
        )

        self.assertTrue(labor_item.is_labor())
        self.assertTrue(material_item.is_material())
        self.assertTrue(equipment_item.is_equipment())
        self.assertTrue(lump_sum_item.is_lump_sum())
        self.assertTrue(other_item.is_other())

    def test_product_or_service_display_returns_user_facing_role_names(self):
        items = self.create_items(self.create_entity_setup())

        self.assertEqual(items["product"].product_or_service_display(), "product")
        self.assertEqual(items["service"].product_or_service_display(), "service")
        self.assertIsNone(items["expense"].product_or_service_display())

    def test_clean_requires_role_specific_accounts(self):
        setup = self.create_entity_setup()

        invalid_product = self.make_item(setup, item_role=ItemModel.ITEM_ROLE_PRODUCT)
        invalid_service = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_SERVICE,
            item_type=ItemModel.ITEM_TYPE_LABOR,
        )
        invalid_expense = self.make_item(setup, item_role=ItemModel.ITEM_ROLE_EXPENSE)
        invalid_inventory = self.make_item(setup, item_role=ItemModel.ITEM_ROLE_INVENTORY)

        with self.assertRaises(ItemModelValidationError):
            invalid_product.clean()
        with self.assertRaises(ItemModelValidationError):
            invalid_service.clean()
        with self.assertRaises(ItemModelValidationError):
            invalid_expense.clean()
        with self.assertRaises(ItemModelValidationError):
            invalid_inventory.clean()

    def test_clean_accepts_representative_valid_role_account_combinations(self):
        setup = self.create_entity_setup()

        valid_product = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_PRODUCT,
            inventory_account=setup["inventory_account"],
            cogs_account=setup["cogs_account"],
            earnings_account=setup["earnings_account"],
        )
        valid_service = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_SERVICE,
            item_type=ItemModel.ITEM_TYPE_LABOR,
            cogs_account=setup["cogs_account"],
            earnings_account=setup["earnings_account"],
        )
        valid_expense = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_EXPENSE,
            item_type=ItemModel.ITEM_TYPE_OTHER,
            expense_account=setup["expense_account"],
        )
        valid_inventory = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_INVENTORY,
            inventory_account=setup["inventory_account"],
        )

        valid_product.clean()
        valid_service.clean()
        valid_expense.clean()
        valid_inventory.clean()

    def test_clean_normalizes_incompatible_accounts_for_each_role(self):
        setup = self.create_entity_setup()

        expense_item = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_EXPENSE,
            item_type=ItemModel.ITEM_TYPE_OTHER,
            expense_account=setup["expense_account"],
            inventory_account=setup["inventory_account"],
            cogs_account=setup["cogs_account"],
            earnings_account=setup["earnings_account"],
        )
        expense_item.clean()
        self.assertIsNone(expense_item.inventory_account)
        self.assertIsNone(expense_item.cogs_account)
        self.assertIsNone(expense_item.earnings_account)
        self.assertFalse(expense_item.for_inventory)
        self.assertFalse(expense_item.is_product_or_service)

        service_item = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_SERVICE,
            item_type=ItemModel.ITEM_TYPE_OTHER,
            expense_account=setup["expense_account"],
            inventory_account=setup["inventory_account"],
            cogs_account=setup["cogs_account"],
            earnings_account=setup["earnings_account"],
        )
        service_item.clean()
        self.assertIsNone(service_item.inventory_account)
        self.assertIsNone(service_item.expense_account)
        self.assertEqual(service_item.item_type, ItemModel.ITEM_TYPE_LABOR)
        self.assertTrue(service_item.is_product_or_service)

        inventory_item = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_INVENTORY,
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            expense_account=setup["expense_account"],
            inventory_account=setup["inventory_account"],
            cogs_account=setup["cogs_account"],
            earnings_account=setup["earnings_account"],
        )
        inventory_item.clean()
        self.assertIsNone(inventory_item.expense_account)
        self.assertIsNone(inventory_item.earnings_account)
        self.assertEqual(inventory_item.inventory_account_id, setup["inventory_account"].uuid)
        self.assertFalse(inventory_item.is_product_or_service)

        product_item = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_PRODUCT,
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            expense_account=setup["expense_account"],
            inventory_account=setup["inventory_account"],
            cogs_account=setup["cogs_account"],
            earnings_account=setup["earnings_account"],
        )
        product_item.clean()
        self.assertIsNone(product_item.expense_account)
        self.assertEqual(product_item.inventory_account_id, setup["inventory_account"].uuid)
        self.assertEqual(product_item.cogs_account_id, setup["cogs_account"].uuid)
        self.assertEqual(product_item.earnings_account_id, setup["earnings_account"].uuid)
        self.assertTrue(product_item.for_inventory)
        self.assertTrue(product_item.is_product_or_service)

    def test_can_generate_item_number_and_generate_commit_false_assigns_number_in_memory(self):
        setup = self.create_entity_setup()
        item_model = self.make_item(
            setup,
            item_role=ItemModel.ITEM_ROLE_PRODUCT,
            inventory_account=setup["inventory_account"],
            cogs_account=setup["cogs_account"],
            earnings_account=setup["earnings_account"],
        )

        self.assertTrue(item_model.can_generate_item_number())

        generated_number = item_model.generate_item_number(commit=False)

        self.assertTrue(generated_number)
        self.assertEqual(item_model.item_number, generated_number)
        self.assertTrue(generated_number.startswith(f"{DJANGO_LEDGER_PRODUCT_NUMBER_PREFIX}-"))
        self.assertFalse(ItemModel.objects.filter(uuid=item_model.uuid).exists())

    def test_generate_item_number_commit_true_persists_number_for_saved_item(self):
        setup = self.create_entity_setup()
        item_model = setup["entity_model"].create_item_expense(
            name="API Item Number Commit Expense",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=setup["uom_model"],
            expense_account=setup["expense_account"],
            commit=True,
        )
        ItemModel.objects.filter(uuid=item_model.uuid).update(item_number="")
        item_model.item_number = ""

        generated_number = item_model.generate_item_number(commit=True)

        item_model.refresh_from_db()
        self.assertEqual(item_model.item_number, generated_number)
        self.assertTrue(generated_number.startswith(f"{DJANGO_LEDGER_EXPENSE_NUMBER_PREFIX}-"))

    def test_item_numbers_advance_within_entity_and_restart_for_other_entity(self):
        setup = self.create_entity_setup(name="API Item Number Entity A")
        other_setup = self.create_entity_setup(name="API Item Number Entity B")

        first_item = setup["entity_model"].create_item_expense(
            name="API First Numbered Expense",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=setup["uom_model"],
            expense_account=setup["expense_account"],
            commit=True,
        )
        second_item = setup["entity_model"].create_item_inventory(
            name="API Second Numbered Inventory",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=setup["uom_model"],
            inventory_account=setup["inventory_account"],
            coa_model=setup["coa_model"],
            commit=True,
        )
        other_first_item = other_setup["entity_model"].create_item_expense(
            name="API Other Entity First Numbered Expense",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=other_setup["uom_model"],
            expense_account=other_setup["expense_account"],
            commit=True,
        )

        self.assertTrue(first_item.item_number.startswith(f"{DJANGO_LEDGER_EXPENSE_NUMBER_PREFIX}-"))
        self.assertTrue(second_item.item_number.startswith(f"{DJANGO_LEDGER_INVENTORY_NUMBER_PREFIX}-"))
        self.assertEqual(self.item_sequence(second_item), self.item_sequence(first_item) + 1)
        self.assertEqual(self.item_sequence(other_first_item), self.item_sequence(first_item))

    def test_get_average_cost_returns_default_or_simple_average(self):
        setup = self.create_entity_setup()
        item_model = setup["entity_model"].create_item_inventory(
            name="API Average Cost Inventory",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=setup["uom_model"],
            inventory_account=setup["inventory_account"],
            coa_model=setup["coa_model"],
            commit=True,
        )

        self.assertEqual(item_model.get_average_cost(), Decimal("0.00"))

        item_model.inventory_received = Decimal("4.000")
        item_model.inventory_received_value = Decimal("50.00")

        self.assertEqual(item_model.get_average_cost(), Decimal("12.5"))
