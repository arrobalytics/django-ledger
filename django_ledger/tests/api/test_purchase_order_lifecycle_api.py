"""
High-level API tests for PurchaseOrderModel lifecycle transitions.
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
from django_ledger.models.purchase_order import PurchaseOrderModelValidationError


class PurchaseOrderLifecycleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_purchase_order_lifecycle_user",
            email="api-purchase-order-lifecycle-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Purchase Order Lifecycle Entity"):
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
            name=f"PO Life Unit {str(entity_model.uuid)[:6]}",
            unit_abbr=f"pl-{str(entity_model.uuid)[:6]}",
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

    def create_purchase_order(self, setup, *, date_draft=date(2025, 1, 15), title="API PO Lifecycle Order"):
        po_model = setup["entity_model"].create_purchase_order(
            po_title=title,
            date_draft=date_draft,
            commit=True,
        )
        po_model.refresh_from_db()
        return po_model

    def migrate_inventory_item(self, po_model, setup, *, quantity="2.00", unit_cost="50.00"):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        po_model.migrate_itemtxs(
            itemtxs={
                setup["inventory_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "total_amount": quantity * unit_cost,
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

        po_model.mark_as_fulfilled(commit=True)
        po_model.refresh_from_db()
        return po_model

    def test_valid_review_and_approval_transitions_set_dates_and_item_statuses(self):
        setup = self.create_entity_setup(name="API PO Lifecycle Valid Entity")
        po_model = self.migrate_inventory_item(self.create_purchase_order(setup), setup)

        po_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        po_model.refresh_from_db()
        self.assertTrue(po_model.is_review())
        self.assertEqual(po_model.date_in_review, date(2025, 1, 16))

        po_model.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))
        po_model.refresh_from_db()
        self.assertTrue(po_model.is_approved())
        self.assertEqual(po_model.date_approved, date(2025, 1, 17))
        self.assertEqual(
            set(po_model.itemtransactionmodel_set.values_list("po_item_status", flat=True)),
            {ItemTransactionModel.STATUS_NOT_ORDERED},
        )

    def test_draft_review_cancel_and_approved_void_set_terminal_status_dates(self):
        setup = self.create_entity_setup(name="API PO Lifecycle Terminal Entity")

        draft_po = self.create_purchase_order(setup)
        draft_po.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))
        draft_po.refresh_from_db()
        self.assertTrue(draft_po.is_canceled())
        self.assertEqual(draft_po.date_canceled, date(2025, 1, 20))

        review_po = self.make_review_purchase_order(setup)
        review_po.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 21))
        review_po.refresh_from_db()
        self.assertTrue(review_po.is_canceled())
        self.assertEqual(review_po.date_canceled, date(2025, 1, 21))

        approved_po = self.make_approved_purchase_order(setup)
        approved_po.mark_as_void(commit=True, void_date=date(2025, 1, 22))
        approved_po.refresh_from_db()
        self.assertTrue(approved_po.is_void())
        self.assertEqual(approved_po.date_void, date(2025, 1, 22))

    def test_review_can_return_to_draft_and_persist_explicit_draft_date(self):
        setup = self.create_entity_setup(name="API PO Lifecycle Back To Draft Entity")
        po_model = self.make_review_purchase_order(setup)

        po_model.mark_as_draft(commit=True, date_draft=date(2025, 1, 23))
        po_model.refresh_from_db()

        self.assertTrue(po_model.is_draft())
        self.assertEqual(po_model.date_draft, date(2025, 1, 23))

    def test_fulfill_sets_status_date_and_received_amount_when_preconditions_are_met(self):
        setup = self.create_entity_setup(name="API PO Lifecycle Fulfilled Entity")

        po_model = self.make_fulfilled_purchase_order(setup)

        self.assertTrue(po_model.is_fulfilled())
        self.assertIsNotNone(po_model.date_fulfilled)
        self.assertEqual(po_model.po_amount_received, po_model.po_amount)
        self.assertEqual(
            set(po_model.itemtransactionmodel_set.values_list("po_item_status", flat=True)),
            {ItemTransactionModel.STATUS_RECEIVED},
        )

    def test_invalid_transitions_raise_validation_errors(self):
        setup = self.create_entity_setup(name="API PO Lifecycle Invalid Entity")
        draft_po = self.create_purchase_order(setup)

        with self.assertRaises(PurchaseOrderModelValidationError):
            draft_po.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))
        with self.assertRaises(PurchaseOrderModelValidationError):
            draft_po.mark_as_fulfilled(commit=True)

        canceled_po = self.create_purchase_order(setup, title="API Canceled PO")
        canceled_po.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))
        with self.assertRaises(PurchaseOrderModelValidationError):
            canceled_po.mark_as_review(commit=True, date_in_review=date(2025, 1, 21))

        void_po = self.make_approved_purchase_order(setup)
        void_po.mark_as_void(commit=True, void_date=date(2025, 1, 22))
        with self.assertRaises(PurchaseOrderModelValidationError):
            void_po.mark_as_review(commit=True, date_in_review=date(2025, 1, 23))

        fulfilled_po = self.make_fulfilled_purchase_order(setup)
        with self.assertRaises(PurchaseOrderModelValidationError):
            fulfilled_po.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 24))

    def test_review_requires_items_and_amount(self):
        setup = self.create_entity_setup(name="API PO Lifecycle Review Requirement Entity")
        po_model = self.create_purchase_order(setup)

        with self.assertRaises(PurchaseOrderModelValidationError):
            po_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

        zero_amount_po = self.migrate_inventory_item(
            self.create_purchase_order(setup, title="API Zero Amount PO"),
            setup,
            unit_cost="0.00",
        )

        with self.assertRaises(PurchaseOrderModelValidationError):
            zero_amount_po.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

    def test_fulfillment_rejects_unbilled_unpaid_or_unreceived_items(self):
        setup = self.create_entity_setup(name="API PO Lifecycle Fulfillment Requirement Entity")

        unbilled_po = self.make_approved_purchase_order(setup)
        with self.assertRaises(PurchaseOrderModelValidationError):
            unbilled_po.mark_as_fulfilled(commit=True)

        unpaid_po = self.make_approved_purchase_order(setup)
        unpaid_bill = setup["entity_model"].create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_ON_RECEIPT,
            date_draft=date(2025, 1, 18),
            cash_account=setup["cash_account"],
            prepaid_account=setup["prepaid_account"],
            payable_account=setup["payable_account"],
            commit=True,
        )
        unpaid_item_tx = unpaid_po.itemtransactionmodel_set.get()
        unpaid_item_tx.bill_model = unpaid_bill
        unpaid_item_tx.po_item_status = ItemTransactionModel.STATUS_RECEIVED
        unpaid_item_tx.save(update_fields=["bill_model", "po_item_status", "updated"])
        with self.assertRaises(PurchaseOrderModelValidationError):
            unpaid_po.mark_as_fulfilled(commit=True)

        unreceived_po = self.make_approved_purchase_order(setup)
        paid_bill = self.create_paid_bill_for_purchase_order(setup)
        unreceived_item_tx = unreceived_po.itemtransactionmodel_set.get()
        unreceived_item_tx.bill_model = paid_bill
        unreceived_item_tx.po_item_status = ItemTransactionModel.STATUS_ORDERED
        unreceived_item_tx.save(update_fields=["bill_model", "po_item_status", "updated"])
        with self.assertRaises(PurchaseOrderModelValidationError):
            unreceived_po.mark_as_fulfilled(commit=True)

    def test_can_predicates_reflect_purchase_order_statuses(self):
        setup = self.create_entity_setup(name="API PO Lifecycle Predicate Entity")

        draft_po = self.create_purchase_order(setup)
        self.assertFalse(draft_po.can_draft())
        self.assertTrue(draft_po.can_review())
        self.assertFalse(draft_po.can_approve())
        self.assertFalse(draft_po.can_fulfill())
        self.assertTrue(draft_po.can_cancel())
        self.assertFalse(draft_po.can_void())
        self.assertTrue(draft_po.can_delete())
        self.assertTrue(draft_po.can_edit_items())

        review_po = self.make_review_purchase_order(setup)
        self.assertTrue(review_po.can_draft())
        self.assertFalse(review_po.can_review())
        self.assertTrue(review_po.can_approve())
        self.assertFalse(review_po.can_fulfill())
        self.assertTrue(review_po.can_cancel())
        self.assertFalse(review_po.can_void())
        self.assertTrue(review_po.can_delete())
        self.assertFalse(review_po.can_edit_items())

        approved_po = self.make_approved_purchase_order(setup)
        self.assertFalse(approved_po.can_draft())
        self.assertFalse(approved_po.can_approve())
        self.assertTrue(approved_po.can_fulfill())
        self.assertFalse(approved_po.can_cancel())
        self.assertTrue(approved_po.can_void())
        self.assertFalse(approved_po.can_delete())
        self.assertFalse(approved_po.can_edit_items())

        fulfilled_po = self.make_fulfilled_purchase_order(setup)
        self.assertFalse(fulfilled_po.can_fulfill())
        self.assertFalse(fulfilled_po.can_cancel())
        self.assertFalse(fulfilled_po.can_void())
        self.assertFalse(fulfilled_po.can_delete())
        self.assertFalse(fulfilled_po.can_edit_items())

    def test_commit_false_transitions_mutate_in_memory_without_persisting(self):
        setup = self.create_entity_setup(name="API PO Lifecycle Commit False Entity")
        po_model = self.migrate_inventory_item(self.create_purchase_order(setup), setup)

        po_model.mark_as_review(commit=False, date_in_review=date(2025, 1, 16))
        self.assertTrue(po_model.is_review())
        self.assertEqual(po_model.date_in_review, date(2025, 1, 16))
        db_po = PurchaseOrderModel.objects.get(uuid=po_model.uuid)
        self.assertTrue(db_po.is_draft())
        self.assertIsNone(db_po.date_in_review)

        po_model.refresh_from_db()
        po_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        po_model.refresh_from_db()
        po_model.mark_as_approved(commit=False, date_approved=date(2025, 1, 17))
        self.assertTrue(po_model.is_approved())
        self.assertEqual(po_model.date_approved, date(2025, 1, 17))
        db_po = PurchaseOrderModel.objects.get(uuid=po_model.uuid)
        self.assertTrue(db_po.is_review())
        self.assertIsNone(db_po.date_approved)
        self.assertEqual(
            set(db_po.itemtransactionmodel_set.values_list("po_item_status", flat=True)),
            {ItemTransactionModel.STATUS_NOT_ORDERED},
        )
