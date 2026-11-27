"""
High-level API tests for ItemModel manager and queryset eligibility behavior.
"""

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


class ItemQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_item_queryset_admin",
            email="api-item-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_item_queryset_manager",
            email="api-item-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_item_queryset_other_admin",
            email="api-item-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_item_queryset_unrelated",
            email="api-item-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_item_queryset_superuser",
            email="api-item-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Item Queryset Entity", admin_user=None, manager_user=None):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=admin_user or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        if manager_user is not None:
            entity_model.managers.add(manager_user)

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
            unit_abbr=f"iq-{str(entity_model.uuid)[:6]}",
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

    def create_items(self, setup, *, name_prefix="API Item Queryset"):
        entity_model = setup["entity_model"]
        uom_model = setup["uom_model"]
        product_item = entity_model.create_item_product(
            name=f"{name_prefix} Product",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            coa_model=setup["coa_model"],
            commit=True,
        )
        service_item = entity_model.create_item_service(
            name=f"{name_prefix} Service",
            uom_model=uom_model,
            coa_model=setup["coa_model"],
            commit=True,
        )
        expense_item = entity_model.create_item_expense(
            name=f"{name_prefix} Expense",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=setup["expense_account"],
            commit=True,
        )
        inventory_item = entity_model.create_item_inventory(
            name=f"{name_prefix} Inventory",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=setup["inventory_account"],
            coa_model=setup["coa_model"],
            commit=True,
        )
        return {
            "product": product_item,
            "service": service_item,
            "expense": expense_item,
            "inventory": inventory_item,
        }

    def assert_item_uuids(self, queryset, expected_items):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {item_model.uuid for item_model in expected_items},
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API Item Queryset Entity A")
        other_setup = self.create_entity_setup(
            name="API Item Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        items = self.create_items(setup)
        self.create_items(other_setup, name_prefix="API Other Item Queryset")

        self.assert_item_uuids(ItemModel.objects.for_entity(setup["entity_model"]), items.values())
        self.assert_item_uuids(ItemModel.objects.for_entity(setup["entity_model"].slug), items.values())
        self.assert_item_uuids(ItemModel.objects.for_entity(setup["entity_model"].uuid), items.values())

    def test_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_items(self.create_entity_setup())

        with self.assertRaises(ItemModelValidationError):
            ItemModel.objects.for_entity(object())

        self.assertFalse(ItemModel.objects.for_entity("missing-item-entity-slug").exists())

    def test_for_entity_active_returns_only_active_items(self):
        setup = self.create_entity_setup()
        items = self.create_items(setup)
        items["expense"].is_active = False
        items["expense"].save(update_fields=["is_active", "updated"])

        active_qs = ItemModel.objects.for_entity_active(setup["entity_model"])

        self.assertTrue(active_qs.filter(uuid=items["product"].uuid).exists())
        self.assertFalse(active_qs.filter(uuid=items["expense"].uuid).exists())

    def test_for_user_scopes_to_authorized_users_and_superuser(self):
        setup = self.create_entity_setup(
            name="API Item Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_setup = self.create_entity_setup(
            name="API Item Queryset Other Access Entity",
            admin_user=self.other_admin_user,
        )
        items = self.create_items(setup)
        other_items = self.create_items(other_setup, name_prefix="API Other Access Item")

        self.assert_item_uuids(ItemModel.objects.all().for_user(self.admin_user), items.values())
        self.assert_item_uuids(ItemModel.objects.all().for_user(self.manager_user), items.values())
        self.assertFalse(ItemModel.objects.all().for_user(self.unrelated_user).exists())
        self.assert_item_uuids(
            ItemModel.objects.all().for_user(self.superuser),
            [*items.values(), *other_items.values()],
        )

    def test_role_filters_select_expected_item_categories(self):
        setup = self.create_entity_setup()
        items = self.create_items(setup)
        item_qs = ItemModel.objects.for_entity(setup["entity_model"])

        self.assert_item_uuids(item_qs.products(), [items["product"]])
        self.assert_item_uuids(item_qs.services(), [items["service"]])
        self.assert_item_uuids(item_qs.expenses(), [items["expense"]])
        self.assert_item_uuids(item_qs.inventory_wip(), [items["inventory"]])
        self.assert_item_uuids(item_qs.inventory_all(), [items["product"], items["inventory"]])

    def test_queryset_document_eligibility_helpers_select_expected_roles(self):
        setup = self.create_entity_setup()
        items = self.create_items(setup)
        item_qs = ItemModel.objects.for_entity(setup["entity_model"])

        self.assert_item_uuids(item_qs.invoices(), [items["product"], items["service"]])
        self.assert_item_uuids(item_qs.estimates(), [items["product"], items["service"]])
        self.assert_item_uuids(item_qs.bills(), [items["product"], items["expense"], items["inventory"]])
        self.assert_item_uuids(item_qs.purchase_orders(), [items["product"], items["inventory"]])

    def test_manager_document_eligibility_helpers_scope_to_active_supported_items(self):
        setup = self.create_entity_setup()
        items = self.create_items(setup)
        items["product"].is_active = False
        items["product"].save(update_fields=["is_active", "updated"])

        entity_model = setup["entity_model"]

        self.assert_item_uuids(ItemModel.objects.for_invoice(entity_model), [items["service"]])
        self.assert_item_uuids(ItemModel.objects.for_bill(entity_model), [items["expense"], items["inventory"]])
        self.assert_item_uuids(ItemModel.objects.for_estimate(entity_model), [items["service"]])
