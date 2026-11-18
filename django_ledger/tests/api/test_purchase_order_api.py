"""
High-level API behavior tests for PurchaseOrderModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import ItemTransactionModel, PurchaseOrderModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.purchase_order import PurchaseOrderModelValidationError
from django_ledger.models.vendor import VendorModel


class PurchaseOrderHighLevelAPITest(TestCase):
    """
    High-level behavior tests for PurchaseOrderModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic purchase order/vendor/item lifecycle
    invariants that should remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_purchase_order_contract_user",
            email="api-purchase-order-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_with_purchase_order_setup(
        self,
        *,
        name="API Purchase Order Contract Entity",
    ):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Purchase Order Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        inventory_account = coa_model.create_account(
            code="1510",
            name="API Purchase Order Inventory Account",
            role="asset_ca_inv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        cogs_account = coa_model.create_account(
            code="5010",
            name="API Purchase Order COGS Account",
            role="cogs_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        earnings_account = coa_model.create_account(
            code="4010",
            name="API Purchase Order Earnings Account",
            role="in_operational",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        expense_account = coa_model.create_account(
            code="6010",
            name="API Purchase Order Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        uom_model = entity_model.create_uom(
            name="API Purchase Order Unit",
            unit_abbr="api-po",
            active=True,
            commit=True,
        )

        vendor_model = VendorModel(
            vendor_name="API Purchase Order Vendor",
            entity_model=entity_model,
            description="API Purchase Order Vendor description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()

        inventory_item = entity_model.create_item_inventory(
            name="API Purchase Order Inventory Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=inventory_account,
            coa_model=coa_model,
            commit=True,
        )

        expense_item = entity_model.create_item_expense(
            name="API Purchase Order Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
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
            "vendor_model": vendor_model,
            "inventory_item": inventory_item,
            "expense_item": expense_item,
        }

    def create_configured_purchase_order(self, setup):
        po_model = PurchaseOrderModel()
        po_model.configure(
            entity_slug=setup["entity_model"],
            po_title="API Purchase Order Contract",
            user_model=self.user,
            draft_date=date(2026, 1, 15),
            commit=True,
        )
        return po_model

    def migrate_inventory_item(
        self,
        po_model,
        setup,
        *,
        quantity="3.00",
        unit_cost="20.00",
    ):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)

        itemtxs = {
            setup["inventory_item"].item_number: {
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_amount": quantity * unit_cost,
            }
        }

        po_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=PurchaseOrderModel.ITEMIZE_REPLACE,
            commit=True,
        )

        po_model.refresh_from_db()
        return po_model

    def test_purchase_order_configure_creates_draft_po_under_entity(self):
        setup = self.create_entity_with_purchase_order_setup()

        po_model = self.create_configured_purchase_order(setup)

        self.assertIsInstance(po_model, PurchaseOrderModel)
        self.assertIsNotNone(po_model.uuid)
        self.assertEqual(po_model.entity_id, setup["entity_model"].uuid)
        self.assertTrue(po_model.is_draft())
        self.assertFalse(po_model.is_approved())
        self.assertTrue(po_model.po_number)

    def test_purchase_order_item_migration_creates_item_transaction(self):
        setup = self.create_entity_with_purchase_order_setup()
        po_model = self.create_configured_purchase_order(setup)

        self.migrate_inventory_item(po_model, setup)

        item_txs = ItemTransactionModel.objects.filter(po_model=po_model)

        self.assertEqual(item_txs.count(), 1)

        item_tx = item_txs.get()

        self.assertEqual(item_tx.item_model_id, setup["inventory_item"].uuid)
        self.assertEqual(item_tx.po_quantity, Decimal("3.00"))
        self.assertEqual(item_tx.po_unit_cost, Decimal("20.00"))
        self.assertEqual(item_tx.po_total_amount, Decimal("60.00"))

    def test_purchase_order_item_migration_updates_po_amount(self):
        setup = self.create_entity_with_purchase_order_setup()
        po_model = self.create_configured_purchase_order(setup)

        po_model = self.migrate_inventory_item(po_model, setup)

        self.assertEqual(po_model.po_amount, Decimal("60.00"))

    def test_purchase_order_for_entity_queryset_limits_scope(self):
        setup = self.create_entity_with_purchase_order_setup(
            name="API Purchase Order Entity A",
        )
        other_setup = self.create_entity_with_purchase_order_setup(
            name="API Purchase Order Entity B",
        )

        po_model = self.create_configured_purchase_order(setup)
        other_po_model = self.create_configured_purchase_order(other_setup)

        scoped_qs = PurchaseOrderModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(scoped_qs.filter(uuid=po_model.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_po_model.uuid).exists())

    def test_purchase_order_can_move_from_draft_to_review(self):
        setup = self.create_entity_with_purchase_order_setup()
        po_model = self.create_configured_purchase_order(setup)
        po_model = self.migrate_inventory_item(po_model, setup)

        po_model.mark_as_review(commit=True)
        po_model.refresh_from_db()

        self.assertTrue(po_model.is_review())
        self.assertFalse(po_model.is_draft())

    def test_purchase_order_can_move_from_review_to_approved(self):
        setup = self.create_entity_with_purchase_order_setup()
        po_model = self.create_configured_purchase_order(setup)
        po_model = self.migrate_inventory_item(po_model, setup)

        po_model.mark_as_review(commit=True)
        po_model.refresh_from_db()

        po_model.mark_as_approved(commit=True)
        po_model.refresh_from_db()

        self.assertTrue(po_model.is_approved())
        self.assertFalse(po_model.is_draft())

    def test_approved_purchase_order_with_unbilled_items_cannot_be_marked_fulfilled(self):
        setup = self.create_entity_with_purchase_order_setup()
        po_model = self.create_configured_purchase_order(setup)
        po_model = self.migrate_inventory_item(po_model, setup)

        po_model.mark_as_review(commit=True)
        po_model.refresh_from_db()

        po_model.mark_as_approved(commit=True)
        po_model.refresh_from_db()

        with self.assertRaises(PurchaseOrderModelValidationError):
            po_model.mark_as_fulfilled(commit=True)

        po_model.refresh_from_db()

        self.assertTrue(po_model.is_approved())
        self.assertFalse(po_model.is_fulfilled())
