"""
Smoke tests for PurchaseOrderModel URL, display, and lifecycle signal behavior.
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
from django_ledger.models.signals import (
    po_status_approved,
    po_status_canceled,
    po_status_draft,
    po_status_fulfilled,
    po_status_in_review,
    po_status_void,
)


class PurchaseOrderURLSignalAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_purchase_order_url_signal_user",
            email="api-purchase-order-url-signal-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Purchase Order URL Signal Entity"):
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
            name=f"PO URL Unit {str(entity_model.uuid)[:6]}",
            unit_abbr=f"pu-{str(entity_model.uuid)[:6]}",
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

    def create_purchase_order(self, setup, *, title="API Purchase Order URL Signal PO"):
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

    def make_review_purchase_order(self, setup):
        po_model = self.migrate_inventory_item(self.create_purchase_order(setup), setup)
        po_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        po_model.refresh_from_db()
        return po_model

    def make_approved_purchase_order(self, setup):
        po_model = self.make_review_purchase_order(setup)
        po_model.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))
        po_model.refresh_from_db()
        return po_model

    def create_paid_bill_for_purchase_order(self, setup):
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

    def make_fulfilled_purchase_order(self, setup):
        po_model = self.make_approved_purchase_order(setup)
        bill_model = self.create_paid_bill_for_purchase_order(setup)
        item_tx = po_model.itemtransactionmodel_set.get()
        item_tx.bill_model = bill_model
        item_tx.po_item_status = ItemTransactionModel.STATUS_RECEIVED
        item_tx.save(update_fields=["bill_model", "po_item_status", "updated"])

        po_model.mark_as_fulfilled(commit=True, date_fulfilled=date(2025, 1, 19))
        po_model.refresh_from_db()
        return po_model

    def collect_signal_calls(self, signal):
        calls = []
        dispatch_uid = f"{self.id()}-{id(signal)}"

        def receiver(sender, **kwargs):
            calls.append(kwargs)

        signal.connect(
            receiver,
            sender=PurchaseOrderModel,
            weak=False,
            dispatch_uid=dispatch_uid,
        )
        self.addCleanup(
            signal.disconnect,
            sender=PurchaseOrderModel,
            dispatch_uid=dispatch_uid,
        )
        return calls

    def assert_signal_received_once(self, calls, po_model, *, commit):
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["instance"], po_model)
        self.assertEqual(calls[0]["commited"], commit)

    def assert_entity_po_url(self, url, setup, po_model):
        self.assertIsInstance(url, str)
        self.assertIn(setup["entity_model"].slug, url)
        self.assertIn(str(po_model.uuid), url)

    def test_action_url_helpers_return_entity_scoped_strings(self):
        setup = self.create_entity_setup(name="API Purchase Order URL Helper Entity")
        po_model = self.create_purchase_order(setup)

        url_helpers = [
            po_model.get_mark_as_draft_url,
            po_model.get_mark_as_review_url,
            po_model.get_mark_as_approved_url,
            po_model.get_mark_as_fulfilled_url,
            po_model.get_mark_as_canceled_url,
            po_model.get_mark_as_void_url,
        ]

        for helper in url_helpers:
            self.assert_entity_po_url(helper(), setup, po_model)

    def test_display_message_and_html_helpers_include_stable_context(self):
        setup = self.create_entity_setup(name="API Purchase Order Display Helper Entity")
        po_model = self.create_purchase_order(setup)

        self.assertIn(po_model.po_number, str(po_model))
        self.assertIn(po_model.get_po_status_display(), str(po_model))

        html_helpers = [
            po_model.get_mark_as_draft_html_id,
            po_model.get_mark_as_review_html_id,
            po_model.get_mark_as_approved_html_id,
            po_model.get_mark_as_fulfilled_html_id,
            po_model.get_mark_as_canceled_html_id,
            po_model.get_mark_as_void_html_id,
        ]
        for helper in html_helpers:
            self.assertIn(str(po_model.uuid), helper())

        message_helpers = [
            po_model.get_mark_as_draft_message,
            po_model.get_mark_as_review_message,
            po_model.get_mark_as_approved_message,
            po_model.get_mark_as_fulfilled_message,
            po_model.get_mark_as_canceled_message,
            po_model.get_mark_as_void_message,
        ]
        for helper in message_helpers:
            self.assertIn(po_model.po_number, helper())

    def test_status_action_date_reflects_current_status_date(self):
        setup = self.create_entity_setup(name="API Purchase Order Status Date Entity")

        draft_po = self.create_purchase_order(setup)
        self.assertEqual(draft_po.get_status_action_date(), date(2025, 1, 15))

        review_po = self.make_review_purchase_order(setup)
        self.assertEqual(review_po.get_status_action_date(), date(2025, 1, 16))

        approved_po = self.make_approved_purchase_order(setup)
        self.assertEqual(approved_po.get_status_action_date(), date(2025, 1, 17))

        canceled_po = self.create_purchase_order(setup, title="API Canceled PO")
        canceled_po.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 18))
        canceled_po.refresh_from_db()
        self.assertEqual(canceled_po.get_status_action_date(), date(2025, 1, 18))

        fulfilled_setup = self.create_entity_setup(name="API Purchase Order Fulfilled Status Date Entity")
        fulfilled_po = self.make_fulfilled_purchase_order(fulfilled_setup)
        self.assertEqual(fulfilled_po.get_status_action_date(), date(2025, 1, 19))

        void_setup = self.create_entity_setup(name="API Purchase Order Void Status Date Entity")
        void_po = self.make_approved_purchase_order(void_setup)
        void_po.mark_as_void(commit=True, void_date=date(2025, 1, 20))
        void_po.refresh_from_db()
        self.assertEqual(void_po.get_status_action_date(), date(2025, 1, 20))

    def test_mark_as_review_emits_purchase_order_status_in_review_signal(self):
        setup = self.create_entity_setup(name="API Purchase Order Review Signal Entity")
        po_model = self.migrate_inventory_item(self.create_purchase_order(setup), setup)
        calls = self.collect_signal_calls(po_status_in_review)

        po_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

        self.assert_signal_received_once(calls, po_model, commit=True)

    def test_mark_as_draft_emits_purchase_order_status_draft_signal(self):
        setup = self.create_entity_setup(name="API Purchase Order Draft Signal Entity")
        po_model = self.make_review_purchase_order(setup)
        calls = self.collect_signal_calls(po_status_draft)

        po_model.mark_as_draft(commit=True, date_draft=date(2025, 1, 17))

        self.assert_signal_received_once(calls, po_model, commit=True)

    def test_mark_as_approved_emits_purchase_order_status_approved_signal(self):
        setup = self.create_entity_setup(name="API Purchase Order Approved Signal Entity")
        po_model = self.make_review_purchase_order(setup)
        calls = self.collect_signal_calls(po_status_approved)

        po_model.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))

        self.assert_signal_received_once(calls, po_model, commit=True)

    def test_mark_as_fulfilled_emits_purchase_order_status_fulfilled_signal(self):
        setup = self.create_entity_setup(name="API Purchase Order Fulfilled Signal Entity")
        po_model = self.make_approved_purchase_order(setup)
        bill_model = self.create_paid_bill_for_purchase_order(setup)
        item_tx = po_model.itemtransactionmodel_set.get()
        item_tx.bill_model = bill_model
        item_tx.po_item_status = ItemTransactionModel.STATUS_RECEIVED
        item_tx.save(update_fields=["bill_model", "po_item_status", "updated"])
        calls = self.collect_signal_calls(po_status_fulfilled)

        po_model.mark_as_fulfilled(commit=True, date_fulfilled=date(2025, 1, 19))

        self.assert_signal_received_once(calls, po_model, commit=True)

    def test_mark_as_canceled_emits_purchase_order_status_canceled_signal(self):
        setup = self.create_entity_setup(name="API Purchase Order Canceled Signal Entity")
        po_model = self.create_purchase_order(setup)
        calls = self.collect_signal_calls(po_status_canceled)

        po_model.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))

        self.assert_signal_received_once(calls, po_model, commit=True)

    def test_mark_as_void_emits_purchase_order_status_void_signal(self):
        setup = self.create_entity_setup(name="API Purchase Order Void Signal Entity")
        po_model = self.make_approved_purchase_order(setup)
        calls = self.collect_signal_calls(po_status_void)

        po_model.mark_as_void(commit=True, void_date=date(2025, 1, 21))

        self.assert_signal_received_once(calls, po_model, commit=True)
