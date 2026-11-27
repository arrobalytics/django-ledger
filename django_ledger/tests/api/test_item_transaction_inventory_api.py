"""
High-level API tests for ItemTransactionModel inventory helper behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_INVENTORY,
    ASSET_CA_PREPAID,
    ASSET_CA_RECEIVABLES,
    COGS,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
    LIABILITY_CL_DEFERRED_REVENUE,
)
from django_ledger.models import BillModel, InvoiceModel, ItemTransactionModel, PurchaseOrderModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.vendor import VendorModel


class ItemTransactionInventoryAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_itemtx_inventory_admin",
            email="api-itemtx-inventory-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API ItemTx Inventory Entity"):
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
        cash_account = entity_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role=ASSET_CA_CASH,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        receivable_account = entity_model.create_account(
            code="1210",
            name=f"{name} Receivable Account",
            role=ASSET_CA_RECEIVABLES,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        prepaid_account = entity_model.create_account(
            code="1310",
            name=f"{name} Prepaid Account",
            role=ASSET_CA_PREPAID,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        inventory_account = entity_model.create_account(
            code="1510",
            name=f"{name} Inventory Account",
            role=ASSET_CA_INVENTORY,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        payable_account = entity_model.create_account(
            code="2010",
            name=f"{name} Accounts Payable",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        unearned_account = entity_model.create_account(
            code="2310",
            name=f"{name} Deferred Revenue",
            role=LIABILITY_CL_DEFERRED_REVENUE,
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        entity_model.create_account(
            code="5010",
            name=f"{name} COGS Account",
            role=COGS,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        entity_model.create_account(
            code="4010",
            name=f"{name} Income Account",
            role=INCOME_OPERATIONAL,
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        expense_account = entity_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role=EXPENSE_OPERATIONAL,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f"{name} Unit",
            unit_abbr=f"ipi-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )
        vendor_model = entity_model.create_vendor(
            {
                "vendor_name": f"{name} Vendor",
                "description": f"{name} Vendor description",
                "active": True,
                "hidden": False,
            },
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
        inventory_item = entity_model.create_item_inventory(
            name=f"{name} Inventory Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=inventory_account,
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
            "prepaid_account": prepaid_account,
            "inventory_account": inventory_account,
            "payable_account": payable_account,
            "unearned_account": unearned_account,
            "uom_model": uom_model,
            "vendor_model": vendor_model,
            "customer_model": customer_model,
            "inventory_item": inventory_item,
            "expense_item": expense_item,
        }

    def create_bill(self, setup):
        return setup["entity_model"].create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_ON_RECEIPT,
            date_draft=date(2026, 1, 15),
            cash_account=setup["cash_account"],
            prepaid_account=setup["prepaid_account"],
            payable_account=setup["payable_account"],
            coa_model=setup["coa_model"],
            commit=True,
        )

    def create_invoice(self, setup):
        return setup["entity_model"].create_invoice(
            customer_model=setup["customer_model"],
            terms=InvoiceModel.TERMS_ON_RECEIPT,
            date_draft=date(2026, 1, 15),
            cash_account=setup["cash_account"],
            prepaid_account=setup["receivable_account"],
            payable_account=setup["unearned_account"],
            coa_model=setup["coa_model"],
            commit=True,
        )

    def create_approved_purchase_order(self, setup):
        po_model = setup["entity_model"].create_purchase_order(
            po_title="API ItemTx Inventory Purchase Order",
            date_draft=date(2026, 1, 10),
            commit=True,
        )
        po_model.po_status = PurchaseOrderModel.PO_STATUS_APPROVED
        po_model.date_approved = date(2026, 1, 11)
        po_model.save(update_fields=["po_status", "date_approved", "updated"])
        return po_model

    def create_inventory_bill_line(
        self,
        setup,
        *,
        item_model=None,
        quantity=Decimal("3.000"),
        unit_cost=Decimal("20.00"),
        status=ItemTransactionModel.STATUS_RECEIVED,
    ):
        item_tx = ItemTransactionModel(
            item_model=item_model or setup["inventory_item"],
            po_model=self.create_approved_purchase_order(setup),
            bill_model=self.create_bill(setup),
            po_quantity=float(quantity),
            po_unit_cost=float(unit_cost),
            po_item_status=status,
            quantity=float(quantity),
            unit_cost=float(unit_cost),
        )
        item_tx.clean()
        item_tx.save()
        item_tx.refresh_from_db()
        return item_tx

    def create_inventory_invoice_line(
        self,
        setup,
        *,
        item_model=None,
        quantity=Decimal("2.000"),
        unit_cost=Decimal("25.00"),
    ):
        item_tx = ItemTransactionModel(
            item_model=item_model or setup["inventory_item"],
            invoice_model=self.create_invoice(setup),
            quantity=float(quantity),
            unit_cost=float(unit_cost),
        )
        item_tx.clean()
        item_tx.save()
        item_tx.refresh_from_db()
        return item_tx

    def test_create_item_inventory_accepts_explicit_account_without_explicit_coa(self):
        setup = self.create_entity_setup()

        item_model = setup["entity_model"].create_item_inventory(
            name="API Explicit Account Inventory Item",
            uom_model=setup["uom_model"],
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            inventory_account=setup["inventory_account"],
            coa_model=None,
            commit=True,
        )

        self.assertEqual(item_model.entity_id, setup["entity_model"].uuid)
        self.assertEqual(item_model.inventory_account_id, setup["inventory_account"].uuid)
        self.assertTrue(item_model.is_inventory())

    def test_inventory_count_aggregates_received_and_invoiced_inventory(self):
        setup = self.create_entity_setup()
        item_model = setup["inventory_item"]
        self.create_inventory_bill_line(
            setup,
            item_model=item_model,
            quantity=Decimal("5.000"),
            unit_cost=Decimal("10.00"),
        )
        self.create_inventory_invoice_line(
            setup,
            item_model=item_model,
            quantity=Decimal("2.000"),
            unit_cost=Decimal("20.00"),
        )

        inventory_count = ItemTransactionModel.objects.inventory_count(setup["entity_model"])
        counted = inventory_count.get(item_model_id=item_model.uuid)

        self.assertEqual(counted["quantity_received"], Decimal("5"))
        self.assertEqual(counted["cost_received"], Decimal("50"))
        self.assertEqual(counted["quantity_invoiced"], Decimal("2"))
        self.assertEqual(counted["revenue_invoiced"], Decimal("40"))
        self.assertEqual(counted["quantity_onhand"], Decimal("3"))
        self.assertEqual(counted["cost_average"], Decimal("10"))
        self.assertEqual(counted["value_onhand"], Decimal("30"))

    def test_inventory_pipeline_filters_ordered_in_transit_and_received_rows(self):
        setup = self.create_entity_setup()
        ordered_item_tx = self.create_inventory_bill_line(setup, status=ItemTransactionModel.STATUS_ORDERED)
        in_transit_item_tx = self.create_inventory_bill_line(setup, status=ItemTransactionModel.STATUS_IN_TRANSIT)
        received_item_tx = self.create_inventory_bill_line(setup, status=ItemTransactionModel.STATUS_RECEIVED)
        invoiced_item_tx = self.create_inventory_invoice_line(setup)

        pipeline_qs = ItemTransactionModel.objects.inventory_pipeline(setup["entity_model"])

        self.assertTrue(pipeline_qs.filter(uuid=ordered_item_tx.uuid).exists())
        self.assertTrue(pipeline_qs.filter(uuid=in_transit_item_tx.uuid).exists())
        self.assertTrue(pipeline_qs.filter(uuid=received_item_tx.uuid).exists())
        self.assertFalse(pipeline_qs.filter(uuid=invoiced_item_tx.uuid).exists())

        self.assertTrue(ItemTransactionModel.objects.inventory_pipeline_ordered(setup["entity_model"]).filter(uuid=ordered_item_tx.uuid).exists())
        self.assertTrue(ItemTransactionModel.objects.inventory_pipeline_in_transit(setup["entity_model"]).filter(uuid=in_transit_item_tx.uuid).exists())
        self.assertTrue(ItemTransactionModel.objects.inventory_pipeline_received(setup["entity_model"]).filter(uuid=received_item_tx.uuid).exists())

    def test_inventory_pipeline_aggregate_reports_status_totals(self):
        setup = self.create_entity_setup()
        self.create_inventory_bill_line(
            setup,
            quantity=Decimal("2.000"),
            unit_cost=Decimal("10.00"),
            status=ItemTransactionModel.STATUS_ORDERED,
        )
        self.create_inventory_bill_line(
            setup,
            quantity=Decimal("3.000"),
            unit_cost=Decimal("12.00"),
            status=ItemTransactionModel.STATUS_IN_TRANSIT,
        )
        self.create_inventory_bill_line(
            setup,
            quantity=Decimal("4.000"),
            unit_cost=Decimal("15.00"),
            status=ItemTransactionModel.STATUS_RECEIVED,
        )

        aggregate_by_status = {
            row["po_item_status"]: row
            for row in ItemTransactionModel.objects.inventory_pipeline_aggregate(setup["entity_model"])
        }

        self.assertEqual(aggregate_by_status[ItemTransactionModel.STATUS_ORDERED]["total_quantity"], Decimal("2"))
        self.assertEqual(aggregate_by_status[ItemTransactionModel.STATUS_ORDERED]["total_value"], Decimal("20"))
        self.assertEqual(aggregate_by_status[ItemTransactionModel.STATUS_IN_TRANSIT]["total_quantity"], Decimal("3"))
        self.assertEqual(aggregate_by_status[ItemTransactionModel.STATUS_IN_TRANSIT]["total_value"], Decimal("36"))
        self.assertEqual(aggregate_by_status[ItemTransactionModel.STATUS_RECEIVED]["total_quantity"], Decimal("4"))
        self.assertEqual(aggregate_by_status[ItemTransactionModel.STATUS_RECEIVED]["total_value"], Decimal("60"))

    def test_inventory_invoiced_returns_only_invoiced_inventory_rows(self):
        setup = self.create_entity_setup()
        invoiced_item_tx = self.create_inventory_invoice_line(setup)
        received_item_tx = self.create_inventory_bill_line(setup)
        non_inventory_invoice_tx = self.create_inventory_invoice_line(
            setup,
            item_model=setup["expense_item"],
        )

        invoiced_qs = ItemTransactionModel.objects.inventory_invoiced(setup["entity_model"])

        self.assertTrue(invoiced_qs.filter(uuid=invoiced_item_tx.uuid).exists())
        self.assertFalse(invoiced_qs.filter(uuid=received_item_tx.uuid).exists())
        self.assertFalse(invoiced_qs.filter(uuid=non_inventory_invoice_tx.uuid).exists())
