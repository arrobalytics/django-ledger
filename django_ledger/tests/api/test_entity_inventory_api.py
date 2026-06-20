"""High-level API behavior tests for EntityModel inventory helpers."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io.roles import (
    ASSET_CA_CASH,
    ASSET_CA_INVENTORY,
    ASSET_CA_PREPAID,
    COGS,
    CREDIT,
    DEBIT,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
)
from django_ledger.models import BillModel, ItemTransactionModel, PurchaseOrderModel
from django_ledger.models.entity import EntityModel, EntityModelValidationError
from django_ledger.models.items import ItemModel


class EntityInventoryHighLevelAPITest(TestCase):
    """
    High-level behavior tests for EntityModel inventory helper APIs.

    These tests use direct, deterministic item and item-transaction setup where
    possible so the inventory helper contracts stay visible.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_entity_inventory_user",
            email="api-entity-inventory-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Entity Inventory Contract Entity"):
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

        cash_account = entity_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        prepaid_account = entity_model.create_account(
            code="1310",
            name=f"{name} Prepaid Account",
            role=ASSET_CA_PREPAID,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        inventory_account = entity_model.create_account(
            code="1510",
            name=f"{name} Inventory Account",
            role=ASSET_CA_INVENTORY,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        payable_account = entity_model.create_account(
            code="2010",
            name=f"{name} Accounts Payable",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type=CREDIT,
            active=True,
            is_role_default=True,
        )
        cogs_account = entity_model.create_account(
            code="5010",
            name=f"{name} COGS Account",
            role=COGS,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        earnings_account = entity_model.create_account(
            code="4010",
            name=f"{name} Earnings Account",
            role=INCOME_OPERATIONAL,
            balance_type=CREDIT,
            active=True,
            is_role_default=True,
        )
        expense_account = entity_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )

        uom_model = entity_model.create_uom(
            name=f"{name} Unit",
            unit_abbr=f"inv-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )

        vendor_model = entity_model.create_vendor(
            {
                "vendor_name": f"{name} Vendor",
                "description": "API inventory vendor.",
                "active": True,
                "hidden": False,
            },
            commit=True,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "prepaid_account": prepaid_account,
            "inventory_account": inventory_account,
            "payable_account": payable_account,
            "cogs_account": cogs_account,
            "earnings_account": earnings_account,
            "expense_account": expense_account,
            "uom_model": uom_model,
            "vendor_model": vendor_model,
        }

    def create_inventory_item(
        self,
        setup,
        *,
        name="API Inventory Item",
        inventory_received=None,
        inventory_received_value=None,
    ):
        item_model = setup["entity_model"].create_item_inventory(
            name=name,
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=setup["uom_model"],
            inventory_account=setup["inventory_account"],
            coa_model=setup["coa_model"],
            commit=True,
        )

        if inventory_received is not None or inventory_received_value is not None:
            item_model.inventory_received = inventory_received
            item_model.inventory_received_value = inventory_received_value
            item_model.save(update_fields=["inventory_received", "inventory_received_value", "updated"])
            item_model.refresh_from_db()

        return item_model

    def create_product_item(self, setup, *, name="API Product Item"):
        return setup["entity_model"].create_item_product(
            name=name,
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=setup["uom_model"],
            coa_model=setup["coa_model"],
            commit=True,
        )

    def create_expense_item(self, setup, *, name="API Expense Item"):
        return setup["entity_model"].create_item_expense(
            name=name,
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=setup["uom_model"],
            expense_account=setup["expense_account"],
            coa_model=setup["coa_model"],
            commit=True,
        )

    def create_received_inventory_line(
        self,
        setup,
        item_model,
        *,
        quantity=Decimal("3.000"),
        unit_cost=Decimal("20.00"),
    ):
        entity_model = setup["entity_model"]
        po_model = entity_model.create_purchase_order(
            po_title="API Inventory Purchase Order",
            date_draft=date(2025, 1, 15),
            commit=True,
        )
        po_model.po_status = PurchaseOrderModel.PO_STATUS_APPROVED
        po_model.date_approved = date(2025, 1, 16)
        po_model.save(update_fields=["po_status", "date_approved", "updated"])

        bill_model = entity_model.create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_ON_RECEIPT,
            date_draft=date(2025, 1, 17),
            cash_account=setup["cash_account"],
            prepaid_account=setup["prepaid_account"],
            payable_account=setup["payable_account"],
            coa_model=setup["coa_model"],
            commit=True,
        )

        item_tx = ItemTransactionModel(
            item_model=item_model,
            po_model=po_model,
            bill_model=bill_model,
            po_quantity=float(quantity),
            po_unit_cost=float(unit_cost),
            po_item_status=ItemTransactionModel.STATUS_RECEIVED,
            quantity=float(quantity),
            unit_cost=float(unit_cost),
        )
        item_tx.clean()
        item_tx.save()
        item_tx.refresh_from_db()

        return po_model, bill_model, item_tx

    def test_inventory_adjustment_reports_counted_recorded_and_combined_differences(self):
        counted_only_uuid = uuid4()
        recorded_only_uuid = uuid4()
        combined_uuid = uuid4()

        counted_qs = [
            {
                "item_model_id": counted_only_uuid,
                "item_model__name": "Counted Only",
                "item_model__uom__name": "Each",
                "quantity_onhand": Decimal("5.000"),
                "value_onhand": Decimal("50.00"),
                "cost_average": Decimal("10.00"),
            },
            {
                "item_model_id": combined_uuid,
                "item_model__name": "Combined",
                "item_model__uom__name": "Each",
                "quantity_onhand": Decimal("8.000"),
                "value_onhand": Decimal("96.00"),
                "cost_average": Decimal("12.00"),
            },
        ]
        recorded_qs = [
            {
                "uuid": recorded_only_uuid,
                "name": "Recorded Only",
                "uom__name": "Each",
                "inventory_received": Decimal("2.000"),
                "inventory_received_value": Decimal("30.00"),
            },
            {
                "uuid": combined_uuid,
                "name": "Combined",
                "uom__name": "Each",
                "inventory_received": Decimal("3.000"),
                "inventory_received_value": Decimal("30.00"),
            },
        ]

        adjustment = EntityModel.inventory_adjustment(counted_qs, recorded_qs)

        counted_only = adjustment[(counted_only_uuid, "Counted Only", "Each")]
        recorded_only = adjustment[(recorded_only_uuid, "Recorded Only", "Each")]
        combined = adjustment[(combined_uuid, "Combined", "Each")]

        self.assertEqual(counted_only["count_diff"], Decimal("5.000"))
        self.assertEqual(counted_only["value_diff"], Decimal("50.00"))
        self.assertEqual(recorded_only["count_diff"], Decimal("-2.000"))
        self.assertEqual(recorded_only["value_diff"], Decimal("-30.00"))
        self.assertEqual(combined["count_diff"], Decimal("5.000"))
        self.assertEqual(combined["value_diff"], Decimal("66.00"))

    def test_inventory_query_helpers_expose_inventory_and_wip_items(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]

        inventory_item = self.create_inventory_item(setup, name="API WIP Inventory Item")
        product_item = self.create_product_item(setup)
        expense_item = self.create_expense_item(setup)

        inventory_qs = entity_model.get_items_inventory()
        wip_qs = entity_model.get_items_inventory_wip()

        self.assertTrue(inventory_qs.filter(uuid=inventory_item.uuid).exists())
        self.assertTrue(inventory_qs.filter(uuid=product_item.uuid).exists())
        self.assertFalse(inventory_qs.filter(uuid=expense_item.uuid).exists())

        self.assertTrue(wip_qs.filter(uuid=inventory_item.uuid).exists())
        self.assertFalse(wip_qs.filter(uuid=product_item.uuid).exists())
        self.assertFalse(wip_qs.filter(uuid=expense_item.uuid).exists())

    def test_recorded_inventory_returns_values_or_item_queryset(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        item_model = self.create_inventory_item(
            setup,
            inventory_received=Decimal("4.000"),
            inventory_received_value=Decimal("44.00"),
        )

        values_qs = entity_model.recorded_inventory(as_values=True)
        model_qs = entity_model.recorded_inventory(as_values=False)

        values = values_qs.get(uuid=item_model.uuid)
        self.assertEqual(values["name"], item_model.name)
        self.assertEqual(values["uom__name"], setup["uom_model"].name)
        self.assertEqual(values["inventory_received"], Decimal("4.000"))
        self.assertEqual(values["inventory_received_value"], Decimal("44.00"))

        self.assertTrue(model_qs.filter(uuid=item_model.uuid).exists())
        self.assertIsInstance(model_qs.get(uuid=item_model.uuid), ItemModel)

    def test_update_inventory_commit_false_returns_adjustments_without_persisting(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        item_model = self.create_inventory_item(setup)
        self.create_received_inventory_line(setup, item_model)

        adjustment, counted_qs, recorded_qs = entity_model.update_inventory(commit=False)

        item_key = (item_model.uuid, item_model.name, setup["uom_model"].name)
        self.assertEqual(counted_qs.count(), 1)
        self.assertTrue(recorded_qs.filter(uuid=item_model.uuid).exists())
        self.assertEqual(adjustment[item_key]["counted"], Decimal("3"))
        self.assertEqual(adjustment[item_key]["counted_value"], Decimal("60"))

        item_model.refresh_from_db()
        self.assertIsNone(item_model.inventory_received)
        self.assertIsNone(item_model.inventory_received_value)

    def test_update_inventory_commit_true_updates_recorded_inventory_fields(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        item_model = self.create_inventory_item(setup)
        self.create_received_inventory_line(
            setup,
            item_model,
            quantity=Decimal("5.000"),
            unit_cost=Decimal("12.00"),
        )

        adjustment, counted_qs, recorded_qs = entity_model.update_inventory(commit=True)

        item_key = (item_model.uuid, item_model.name, setup["uom_model"].name)
        self.assertEqual(counted_qs.count(), 1)
        self.assertTrue(recorded_qs.filter(uuid=item_model.uuid).exists())
        self.assertEqual(adjustment[item_key]["counted"], Decimal("5"))
        self.assertEqual(adjustment[item_key]["counted_value"], Decimal("60"))

        item_model.refresh_from_db()
        self.assertEqual(item_model.inventory_received, Decimal("5.000"))
        self.assertEqual(item_model.inventory_received_value, Decimal("60.00"))

    def test_validate_item_qs_rejects_items_from_another_entity(self):
        setup = self.create_entity_setup(name="API Inventory Entity A")
        other_setup = self.create_entity_setup(name="API Inventory Entity B")

        item_model = self.create_inventory_item(setup, name="API Entity A Inventory Item")
        other_item_model = self.create_inventory_item(other_setup, name="API Entity B Inventory Item")

        same_entity_qs = ItemModel.objects.filter(uuid=item_model.uuid)
        mixed_entity_qs = ItemModel.objects.filter(uuid__in=[item_model.uuid, other_item_model.uuid])

        self.assertTrue(setup["entity_model"].validate_item_qs(same_entity_qs))
        self.assertFalse(
            setup["entity_model"].validate_item_qs(
                mixed_entity_qs,
                raise_exception=False,
            )
        )

        with self.assertRaises(EntityModelValidationError):
            setup["entity_model"].validate_item_qs(mixed_entity_qs)
