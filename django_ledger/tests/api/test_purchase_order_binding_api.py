"""
High-level API tests for PurchaseOrderModel estimate and bill binding behavior.
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
from django_ledger.models import BillModel, EstimateModel, ItemTransactionModel, PurchaseOrderModel
from django_ledger.models.bill import BillModelValidationError
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.purchase_order import PurchaseOrderModelValidationError


class PurchaseOrderBindingAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_purchase_order_binding_user",
            email="api-purchase-order-binding-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Purchase Order Binding Entity"):
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
            name=f"PO Bind Unit {str(entity_model.uuid)[:6]}",
            unit_abbr=f"pb-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )
        customer_model = CustomerModel(
            customer_name=f"{name} Customer",
            entity_model=entity_model,
            description=f"{name} customer.",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        vendor_model = entity_model.create_vendor(
            {
                "vendor_name": f"{name} Vendor",
                "description": f"{name} vendor.",
                "active": True,
                "hidden": False,
            },
            commit=True,
        )
        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
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
        return {
            "entity_model": entity_model,
            "customer_model": customer_model,
            "vendor_model": vendor_model,
            "cash_account": cash_account,
            "prepaid_account": prepaid_account,
            "payable_account": payable_account,
            "service_item": service_item,
            "inventory_item": inventory_item,
        }

    def create_estimate(self, setup, *, title="API Purchase Order Binding Estimate"):
        estimate_model = setup["entity_model"].create_estimate(
            estimate_title=title,
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=setup["customer_model"],
            date_draft=date(2025, 1, 15),
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def migrate_estimate_item(self, estimate_model, setup):
        estimate_model.migrate_itemtxs(
            itemtxs={
                setup["service_item"].item_number: {
                    "quantity": Decimal("1.00"),
                    "unit_cost": Decimal("100.00"),
                    "unit_revenue": Decimal("150.00"),
                    "total_amount": Decimal("150.00"),
                }
            },
            operation=EstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def make_review_estimate(self, setup, *, title="API Purchase Order Binding Review Estimate"):
        estimate_model = self.migrate_estimate_item(self.create_estimate(setup, title=title), setup)
        estimate_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        estimate_model.refresh_from_db()
        return estimate_model

    def make_approved_estimate(self, setup, *, title="API Purchase Order Binding Approved Estimate"):
        estimate_model = self.make_review_estimate(setup, title=title)
        estimate_model.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))
        estimate_model.refresh_from_db()
        return estimate_model

    def create_purchase_order(self, setup, *, title="API Purchase Order Binding PO", date_draft=date(2025, 1, 18)):
        po_model = setup["entity_model"].create_purchase_order(
            po_title=title,
            date_draft=date_draft,
            commit=True,
        )
        po_model.refresh_from_db()
        return po_model

    def make_approved_purchase_order(
        self,
        setup,
        *,
        title="API Purchase Order Binding Approved PO",
        date_approved=date(2025, 1, 20),
    ):
        po_model = self.create_purchase_order(setup, title=title, date_draft=date(2025, 1, 18))
        self.migrate_purchase_order_item(po_model, setup)
        po_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 19))
        po_model.refresh_from_db()
        po_model.mark_as_approved(commit=True, date_approved=date_approved)
        po_model.refresh_from_db()
        return po_model

    def migrate_purchase_order_item(self, po_model, setup):
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

    def create_bill(self, setup, *, date_draft=date(2025, 1, 21)):
        bill_model = setup["entity_model"].create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_ON_RECEIPT,
            date_draft=date_draft,
            cash_account=setup["cash_account"],
            prepaid_account=setup["prepaid_account"],
            payable_account=setup["payable_account"],
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def test_approved_same_entity_estimate_can_bind_to_purchase_order(self):
        setup = self.create_entity_setup()
        estimate_model = self.make_approved_estimate(setup)
        po_model = self.create_purchase_order(setup)

        self.assertTrue(po_model.can_bind_estimate(estimate_model))

        po_model.action_bind_estimate(estimate_model, commit=True)
        po_model.refresh_from_db()

        self.assertEqual(po_model.ce_model_id, estimate_model.uuid)
        self.assertTrue(po_model.is_contract_bound())
        self.assertTrue(estimate_model.purchaseordermodel_set.filter(uuid=po_model.uuid).exists())

    def test_unapproved_estimate_cannot_bind_to_purchase_order(self):
        setup = self.create_entity_setup(name="API Purchase Order Binding Unapproved Entity")
        draft_estimate = self.create_estimate(setup, title="API Draft Estimate")
        review_estimate = self.make_review_estimate(setup)
        po_model = self.create_purchase_order(setup)

        self.assertFalse(po_model.can_bind_estimate(draft_estimate))
        self.assertFalse(po_model.can_bind_estimate(review_estimate))

        with self.assertRaises(PurchaseOrderModelValidationError):
            po_model.action_bind_estimate(draft_estimate, commit=True)
        with self.assertRaises(PurchaseOrderModelValidationError):
            po_model.action_bind_estimate(review_estimate, commit=True)

        po_model.refresh_from_db()
        self.assertIsNone(po_model.ce_model_id)

    def test_cross_entity_estimate_cannot_bind_to_purchase_order(self):
        setup = self.create_entity_setup(name="API Purchase Order Binding Entity A")
        other_setup = self.create_entity_setup(name="API Purchase Order Binding Entity B")
        other_estimate = self.make_approved_estimate(other_setup)
        po_model = self.create_purchase_order(setup)

        self.assertFalse(po_model.can_bind_estimate(other_estimate))

        with self.assertRaises(PurchaseOrderModelValidationError):
            po_model.action_bind_estimate(other_estimate, commit=True)

        po_model.refresh_from_db()
        self.assertIsNone(po_model.ce_model_id)

    def test_already_bound_purchase_order_rejects_second_estimate(self):
        setup = self.create_entity_setup(name="API Purchase Order Binding Already Bound Entity")
        first_estimate = self.make_approved_estimate(setup, title="API First Estimate")
        second_estimate = self.make_approved_estimate(setup, title="API Second Estimate")
        po_model = self.create_purchase_order(setup)
        po_model.action_bind_estimate(first_estimate, commit=True)
        po_model.refresh_from_db()

        self.assertFalse(po_model.can_bind_estimate(second_estimate))

        with self.assertRaises(PurchaseOrderModelValidationError):
            po_model.action_bind_estimate(second_estimate, commit=True)

        po_model.refresh_from_db()
        self.assertEqual(po_model.ce_model_id, first_estimate.uuid)

    def test_configure_can_bind_approved_estimate_at_creation_time(self):
        setup = self.create_entity_setup(name="API Purchase Order Binding Configure Entity")
        estimate_model = self.make_approved_estimate(setup)

        po_model = setup["entity_model"].create_purchase_order(
            po_title="API Purchase Order Configured With Estimate",
            estimate_model=estimate_model,
            date_draft=date(2025, 1, 18),
            commit=True,
        )
        po_model.refresh_from_db()

        self.assertEqual(po_model.ce_model_id, estimate_model.uuid)
        self.assertTrue(po_model.is_contract_bound())

    def test_bill_can_bind_approved_purchase_order_and_link_po_items(self):
        setup = self.create_entity_setup(name="API Purchase Order Binding Bill Entity")
        po_model = self.make_approved_purchase_order(setup)
        bill_model = self.create_bill(setup)

        self.assertTrue(bill_model.can_bind_po(po_model))

        item_tx = po_model.itemtransactionmodel_set.get()
        item_tx.bill_model = bill_model
        item_tx.save(update_fields=["bill_model", "updated"])

        self.assertTrue(po_model.get_po_bill_queryset().filter(uuid=bill_model.uuid).exists())

    def test_bill_rejects_unapproved_or_late_approved_purchase_order(self):
        setup = self.create_entity_setup(name="API Purchase Order Binding Bill Rejection Entity")
        draft_po = self.create_purchase_order(setup)
        review_po = self.migrate_purchase_order_item(
            self.create_purchase_order(setup, title="API Review PO"),
            setup,
        )
        review_po.mark_as_review(commit=True, date_in_review=date(2025, 1, 19))
        review_po.refresh_from_db()
        bill_model = self.create_bill(setup, date_draft=date(2025, 1, 21))

        self.assertFalse(bill_model.can_bind_po(draft_po))
        self.assertFalse(bill_model.can_bind_po(review_po))

        with self.assertRaises(BillModelValidationError):
            bill_model.can_bind_po(draft_po, raise_exception=True)
        with self.assertRaises(BillModelValidationError):
            bill_model.can_bind_po(review_po, raise_exception=True)

        late_po = self.make_approved_purchase_order(
            setup,
            title="API Late Approved PO",
            date_approved=date(2025, 1, 22),
        )

        self.assertFalse(bill_model.can_bind_po(late_po))
        with self.assertRaises(BillModelValidationError):
            bill_model.can_bind_po(late_po, raise_exception=True)

    def test_cross_entity_bill_cannot_bind_purchase_order(self):
        setup = self.create_entity_setup(name="API Purchase Order Binding Bill Entity A")
        other_setup = self.create_entity_setup(name="API Purchase Order Binding Bill Entity B")
        po_model = self.make_approved_purchase_order(setup)
        other_bill = self.create_bill(other_setup)

        self.assertFalse(other_bill.can_bind_po(po_model))

        with self.assertRaises(BillModelValidationError):
            other_bill.can_bind_po(po_model, raise_exception=True)
