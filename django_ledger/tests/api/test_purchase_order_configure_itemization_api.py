"""
High-level API tests for PurchaseOrderModel configuration and itemization behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_INVENTORY,
    COGS,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
)
from django_ledger.models import ItemTransactionModel, PurchaseOrderModel
from django_ledger.models.entity import EntityModel, EntityStateModel
from django_ledger.models.items import ItemModel
from django_ledger.models.purchase_order import PurchaseOrderModelValidationError
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING


class PurchaseOrderConfigureItemizationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_purchase_order_configure_user",
            email="api-purchase-order-configure-user@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_purchase_order_configure_unrelated",
            email="api-purchase-order-configure-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Purchase Order Configure Entity"):
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
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role=EXPENSE_OPERATIONAL,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f"PO Unit {str(entity_model.uuid)[:6]}",
            unit_abbr=f"po-{str(entity_model.uuid)[:6]}",
            active=True,
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
        product_item = entity_model.create_item_product(
            name=f"{name} Product Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )
        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
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
            "inventory_item": inventory_item,
            "product_item": product_item,
            "service_item": service_item,
            "expense_item": expense_item,
        }

    def configure_purchase_order(
        self,
        setup,
        *,
        entity_input=None,
        user_model=None,
        draft_date=date(2026, 1, 15),
        commit=True,
        title="API Purchase Order Configure PO",
    ):
        po_model = PurchaseOrderModel()
        po_model.configure(
            entity_slug=setup["entity_model"] if entity_input is None else entity_input,
            po_title=title,
            user_model=self.user if user_model is None else user_model,
            draft_date=draft_date,
            commit=commit,
        )
        if commit:
            po_model.refresh_from_db()
        return po_model

    def migrate_inventory_item(
        self,
        po_model,
        setup,
        *,
        quantity="2.00",
        unit_cost="50.00",
        operation=None,
    ):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        itemtxs_batch = po_model.migrate_itemtxs(
            itemtxs={
                setup["inventory_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "total_amount": quantity * unit_cost,
                }
            },
            operation=operation or PurchaseOrderModel.ITEMIZE_REPLACE,
            commit=True,
        )
        po_model.refresh_from_db()
        return po_model, itemtxs_batch

    def migrate_product_item(self, po_model, setup, *, quantity="1.00", unit_cost="20.00"):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        itemtxs_batch = po_model.migrate_itemtxs(
            itemtxs={
                setup["product_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "total_amount": quantity * unit_cost,
                }
            },
            operation=PurchaseOrderModel.ITEMIZE_APPEND,
            commit=True,
        )
        po_model.refresh_from_db()
        return po_model, itemtxs_batch

    def assert_number_ends_with_sequence(self, number, sequence):
        self.assertTrue(
            number.endswith(str(sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)),
            msg=f"{number!r} does not end with sequence {sequence}",
        )

    def test_configure_accepts_entity_model_and_authorized_slug_but_not_uuid(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]

        by_model = self.configure_purchase_order(setup, entity_input=entity_model)
        by_slug = self.configure_purchase_order(setup, entity_input=entity_model.slug)

        self.assertEqual(by_model.entity_id, entity_model.uuid)
        self.assertEqual(by_slug.entity_id, entity_model.uuid)
        self.assertTrue(by_model.po_number)
        self.assertTrue(by_slug.po_number)

        with self.assertRaises(PurchaseOrderModelValidationError):
            self.configure_purchase_order(setup, entity_input=entity_model.uuid)

    def test_configure_rejects_slug_without_user_and_unauthorized_slug(self):
        setup = self.create_entity_setup(name="API Purchase Order Configure Rejection Entity")

        with self.assertRaises(PurchaseOrderModelValidationError):
            PurchaseOrderModel().configure(
                entity_slug=setup["entity_model"].slug,
                po_title="API Rejected Purchase Order",
            )

        with self.assertRaises(Http404):
            self.configure_purchase_order(
                setup,
                entity_input=setup["entity_model"].slug,
                user_model=self.unrelated_user,
            )

    def test_configure_commit_false_generates_number_and_state_without_persisting_purchase_order(self):
        setup = self.create_entity_setup(name="API Purchase Order Configure Commit False Entity")

        po_model = self.configure_purchase_order(setup, commit=False)

        self.assertTrue(po_model.is_configured())
        self.assertTrue(po_model.po_number)
        self.assertEqual(po_model.date_draft, date(2026, 1, 15))
        self.assertFalse(PurchaseOrderModel.objects.filter(uuid=po_model.uuid).exists())

        state_model = EntityStateModel.objects.get(
            entity_model=setup["entity_model"],
            entity_unit__isnull=True,
            fiscal_year=2026,
            key=EntityStateModel.KEY_PURCHASE_ORDER,
        )
        self.assertEqual(state_model.sequence, 1)
        self.assert_number_ends_with_sequence(po_model.po_number, 1)

    def test_generate_po_number_commit_false_and_true_behaviors(self):
        setup = self.create_entity_setup(name="API Purchase Order Configure Number Entity")
        manual_po = PurchaseOrderModel.objects.create(
            entity=setup["entity_model"],
            po_title="API Manual Number Purchase Order",
            po_status=PurchaseOrderModel.PO_STATUS_DRAFT,
            date_draft=date(2026, 1, 15),
            po_number="manual-po-1",
        )
        manual_po.po_number = ""

        self.assertTrue(manual_po.can_generate_po_number())
        generated_number = manual_po.generate_po_number(commit=False)

        self.assertTrue(generated_number)
        self.assertEqual(
            PurchaseOrderModel.objects.get(uuid=manual_po.uuid).po_number,
            "manual-po-1",
        )

        persisted_po = PurchaseOrderModel.objects.create(
            entity=setup["entity_model"],
            po_title="API Persisted Number Purchase Order",
            po_status=PurchaseOrderModel.PO_STATUS_DRAFT,
            date_draft=date(2026, 1, 15),
            po_number="manual-po-2",
        )
        persisted_po.po_number = ""

        persisted_number = persisted_po.generate_po_number(commit=True)

        self.assertTrue(persisted_number)
        self.assertEqual(
            PurchaseOrderModel.objects.get(uuid=persisted_po.uuid).po_number,
            persisted_number,
        )

    def test_get_item_model_qs_returns_purchase_order_eligible_items(self):
        setup = self.create_entity_setup(name="API Purchase Order Configure Item Query Entity")
        po_model = self.configure_purchase_order(setup)

        item_qs = po_model.get_item_model_qs()

        self.assertTrue(item_qs.filter(uuid=setup["inventory_item"].uuid).exists())
        self.assertTrue(item_qs.filter(uuid=setup["product_item"].uuid).exists())
        self.assertFalse(item_qs.filter(uuid=setup["service_item"].uuid).exists())
        self.assertFalse(item_qs.filter(uuid=setup["expense_item"].uuid).exists())

    def test_migrate_itemtxs_replace_and_append_create_purchase_order_items_and_update_amounts(self):
        setup = self.create_entity_setup(name="API Purchase Order Configure Item Migration Entity")
        po_model = self.configure_purchase_order(setup)

        po_model, itemtxs_batch = self.migrate_inventory_item(po_model, setup)

        self.assertEqual(len(itemtxs_batch), 1)
        item_tx = ItemTransactionModel.objects.get(po_model=po_model)
        self.assertEqual(item_tx.item_model_id, setup["inventory_item"].uuid)
        self.assertEqual(item_tx.po_quantity, Decimal("2.00"))
        self.assertEqual(item_tx.po_unit_cost, Decimal("50.00"))
        self.assertEqual(item_tx.po_total_amount, Decimal("100.00"))
        self.assertEqual(po_model.po_amount, Decimal("100.00"))

        po_model, appended_batch = self.migrate_product_item(po_model, setup)

        self.assertEqual(len(appended_batch), 2)
        self.assertEqual(ItemTransactionModel.objects.filter(po_model=po_model).count(), 2)
        self.assertEqual(po_model.po_amount, Decimal("120.00"))

        po_model, replacement_batch = self.migrate_inventory_item(
            po_model,
            setup,
            quantity="1.00",
            unit_cost="25.00",
        )

        self.assertEqual(len(replacement_batch), 1)
        self.assertEqual(ItemTransactionModel.objects.filter(po_model=po_model).count(), 1)
        self.assertEqual(po_model.po_amount, Decimal("25.00"))

    def test_can_migrate_itemtxs_allows_draft_purchase_orders_only(self):
        setup = self.create_entity_setup(name="API Purchase Order Configure Can Migrate Entity")
        po_model = self.configure_purchase_order(setup)

        self.assertTrue(po_model.can_migrate_itemtxs())

        po_model, _itemtxs_batch = self.migrate_inventory_item(po_model, setup)
        po_model.mark_as_review(date_in_review=date(2026, 1, 16), commit=True)
        po_model.refresh_from_db()

        self.assertFalse(po_model.can_migrate_itemtxs())
        self.assertIsNone(
            po_model.migrate_itemtxs(
                itemtxs={
                    setup["inventory_item"].item_number: {
                        "quantity": Decimal("1.00"),
                        "unit_cost": Decimal("10.00"),
                        "total_amount": Decimal("10.00"),
                    }
                },
                operation=PurchaseOrderModel.ITEMIZE_REPLACE,
                commit=True,
            )
        )

    def test_validate_item_transaction_qs_rejects_transactions_from_another_purchase_order(self):
        setup = self.create_entity_setup(name="API Purchase Order Configure Validate ItemTx Entity")
        po_model = self.configure_purchase_order(setup)
        other_po_model = self.configure_purchase_order(setup, title="API Other Purchase Order")
        other_po_model, _itemtxs_batch = self.migrate_inventory_item(other_po_model, setup)
        other_itemtxs = ItemTransactionModel.objects.filter(po_model=other_po_model)

        with self.assertRaises(PurchaseOrderModelValidationError):
            po_model.validate_item_transaction_qs(other_itemtxs)

    def test_get_itemtxs_data_reports_purchase_order_amounts(self):
        setup = self.create_entity_setup(name="API Purchase Order Configure Item Data Entity")
        po_model = self.configure_purchase_order(setup)
        po_model, _itemtxs_batch = self.migrate_inventory_item(po_model, setup)

        itemtxs_qs, itemtxs_data = po_model.get_itemtxs_data()

        self.assertEqual(itemtxs_qs.count(), 1)
        self.assertEqual(itemtxs_data["total_items"], 1)
        self.assertEqual(itemtxs_data["po_total_amount__sum"], Decimal("100.00"))

        aggregate_qs, aggregate_data = po_model.get_itemtxs_data(aggregate_on_db=True)

        self.assertEqual(aggregate_qs.count(), 1)
        self.assertEqual(Decimal(str(aggregate_data["po_total_amount__sum"])), Decimal("100.0"))
        self.assertEqual(aggregate_data["total_items"], 1)

        _lazy_qs, lazy_data = po_model.get_itemtxs_data(lazy_agg=True)

        self.assertIsNone(lazy_data)
