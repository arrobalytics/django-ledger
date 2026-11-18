"""
Focused edge-case API tests for PurchaseOrderModel.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_INVENTORY,
    ASSET_CA_PREPAID,
    COGS,
    INCOME_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
)
from django_ledger.models import BillModel, ItemTransactionModel, PurchaseOrderModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel


class PurchaseOrderEdgeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_purchase_order_edge_user",
            email="api-purchase-order-edge-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Purchase Order Edge Entity"):
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
        inventory_account = coa_model.create_account(
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
            name=f"PO Edge Unit {str(entity_model.uuid)[:6]}",
            unit_abbr=f"pe-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )
        vendor_model = entity_model.create_vendor(
            {
                "vendor_name": f"{name} Vendor",
                "description": f"{name} vendor.",
                "active": True,
                "hidden": False,
            },
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
        return {
            "entity_model": entity_model,
            "vendor_model": vendor_model,
            "cash_account": cash_account,
            "prepaid_account": prepaid_account,
            "payable_account": payable_account,
            "inventory_item": inventory_item,
        }

    def create_purchase_order(self, setup, *, title="API Purchase Order Edge PO"):
        po_model = setup["entity_model"].create_purchase_order(
            po_title=title,
            date_draft=date(2025, 1, 15),
            commit=True,
        )
        po_model.refresh_from_db()
        return po_model

    def migrate_inventory_item(self, po_model, setup):
        po_model.migrate_itemtxs(
            itemtxs={
                setup["inventory_item"].item_number: {
                    "quantity": Decimal("1.00"),
                    "unit_cost": Decimal("100.00"),
                    "total_amount": Decimal("100.00"),
                }
            },
            operation=PurchaseOrderModel.ITEMIZE_REPLACE,
            commit=True,
        )
        po_model.refresh_from_db()
        return po_model

    def make_approved_purchase_order(self, setup, *, title="API Purchase Order Edge Approved PO"):
        po_model = self.migrate_inventory_item(self.create_purchase_order(setup, title=title), setup)
        po_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        po_model.refresh_from_db()
        po_model.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))
        po_model.refresh_from_db()
        return po_model

    def create_paid_bill(self, setup):
        bill_model = setup["entity_model"].create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_ON_RECEIPT,
            date_draft=date(2025, 1, 18),
            cash_account=setup["cash_account"],
            prepaid_account=setup["prepaid_account"],
            payable_account=setup["payable_account"],
            commit=True,
        )
        bill_model.bill_status = BillModel.BILL_STATUS_PAID
        bill_model.amount_due = Decimal("100.00")
        bill_model.amount_paid = Decimal("100.00")
        bill_model.save(update_fields=["bill_status", "amount_due", "amount_paid", "updated"])
        bill_model.refresh_from_db()
        return bill_model

    def attach_bill_to_po_item(self, po_model, bill_model):
        item_tx = po_model.itemtransactionmodel_set.get()
        item_tx.bill_model = bill_model
        item_tx.po_item_status = ItemTransactionModel.STATUS_RECEIVED
        item_tx.save(update_fields=["bill_model", "po_item_status", "updated"])
        return item_tx

    def assert_bill_uuids(self, queryset, expected_bills):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {bill_model.uuid for bill_model in expected_bills},
        )

    def test_mark_as_fulfilled_accepts_prefetched_item_transaction_list(self):
        setup = self.create_entity_setup(name="API Purchase Order Edge Fulfill List Entity")
        po_model = self.make_approved_purchase_order(setup)
        bill_model = self.create_paid_bill(setup)
        self.attach_bill_to_po_item(po_model, bill_model)
        po_items = list(po_model.itemtransactionmodel_set.all())

        po_model.mark_as_fulfilled(po_items=po_items, commit=True, date_fulfilled=date(2025, 1, 19))
        po_model.refresh_from_db()

        self.assertTrue(po_model.is_fulfilled())
        self.assertEqual(po_model.date_fulfilled, date(2025, 1, 19))
        self.assertEqual(po_model.po_amount_received, po_model.po_amount)
        self.assertEqual(
            set(po_model.itemtransactionmodel_set.values_list("po_item_status", flat=True)),
            {ItemTransactionModel.STATUS_RECEIVED},
        )

    def test_get_po_bill_queryset_only_returns_bills_linked_to_this_purchase_order(self):
        setup = self.create_entity_setup(name="API Purchase Order Edge Bill Query Entity")
        po_model = self.make_approved_purchase_order(setup, title="API Purchase Order Edge Linked PO")
        other_po_model = self.make_approved_purchase_order(setup, title="API Purchase Order Edge Other PO")
        bill_model = self.create_paid_bill(setup)
        self.attach_bill_to_po_item(po_model, bill_model)

        self.assert_bill_uuids(po_model.get_po_bill_queryset(), [bill_model])
        self.assertFalse(other_po_model.get_po_bill_queryset().exists())
