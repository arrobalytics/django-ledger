"""
High-level API tests for EstimateModel configuration and itemization behavior.
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
from django_ledger.models import EstimateModel, ItemTransactionModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel, EntityStateModel
from django_ledger.models.estimate import EstimateModelValidationError
from django_ledger.models.items import ItemModel
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING


class EstimateConfigureItemizationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_estimate_configure_user",
            email="api-estimate-configure-user@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_estimate_configure_unrelated",
            email="api-estimate-configure-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Estimate Configure Entity"):
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
        coa_model.create_account(
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
            name=f"{name} Unit",
            unit_abbr=f"e-{str(entity_model.uuid)[:6]}",
            active=True,
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
        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
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
            "customer_model": customer_model,
            "service_item": service_item,
            "product_item": product_item,
            "expense_item": expense_item,
        }

    def configure_estimate(
        self,
        setup,
        *,
        entity_input=None,
        customer_model=None,
        user_model=None,
        date_draft=date(2026, 1, 15),
        commit=True,
        title="API Estimate Configure Contract",
    ):
        estimate_model = EstimateModel(terms=EstimateModel.CONTRACT_TERMS_FIXED)
        estimate_model.configure(
            entity_slug=setup["entity_model"] if entity_input is None else entity_input,
            customer_model=setup["customer_model"] if customer_model is None else customer_model,
            user_model=self.user if user_model is None else user_model,
            date_draft=date_draft,
            estimate_title=title,
            commit=commit,
        )
        if commit:
            estimate_model.refresh_from_db()
        return estimate_model

    def migrate_service_item(
        self,
        estimate_model,
        setup,
        *,
        quantity="2.00",
        unit_cost="50.00",
        unit_revenue="75.00",
        operation=None,
    ):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        unit_revenue = Decimal(unit_revenue)
        itemtxs_batch = estimate_model.migrate_itemtxs(
            itemtxs={
                setup["service_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "unit_revenue": unit_revenue,
                    "total_amount": quantity * unit_revenue,
                }
            },
            operation=operation or EstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model, itemtxs_batch

    def migrate_product_item(self, estimate_model, setup, *, quantity="1.00", unit_cost="20.00", unit_revenue="35.00"):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        unit_revenue = Decimal(unit_revenue)
        itemtxs_batch = estimate_model.migrate_itemtxs(
            itemtxs={
                setup["product_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "unit_revenue": unit_revenue,
                    "total_amount": quantity * unit_revenue,
                }
            },
            operation=EstimateModel.ITEMIZE_APPEND,
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model, itemtxs_batch

    def assert_number_ends_with_sequence(self, number, sequence):
        self.assertTrue(
            number.endswith(str(sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)),
            msg=f"{number!r} does not end with sequence {sequence}",
        )

    def test_configure_accepts_entity_model_authorized_slug_and_authorized_uuid(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]

        by_model = self.configure_estimate(setup, entity_input=entity_model)
        by_slug = self.configure_estimate(setup, entity_input=entity_model.slug)
        by_uuid = self.configure_estimate(setup, entity_input=entity_model.uuid)

        self.assertEqual(by_model.entity_id, entity_model.uuid)
        self.assertEqual(by_slug.entity_id, entity_model.uuid)
        self.assertEqual(by_uuid.entity_id, entity_model.uuid)
        self.assertEqual(by_model.customer_id, setup["customer_model"].uuid)
        self.assertEqual(by_slug.customer_id, setup["customer_model"].uuid)
        self.assertEqual(by_uuid.customer_id, setup["customer_model"].uuid)
        self.assertTrue(by_model.estimate_number)
        self.assertTrue(by_slug.estimate_number)
        self.assertTrue(by_uuid.estimate_number)

    def test_configure_rejects_slug_without_user_and_unauthorized_slug_or_uuid(self):
        setup = self.create_entity_setup(name="API Estimate Configure Rejection Entity")

        with self.assertRaises(EstimateModelValidationError):
            EstimateModel(terms=EstimateModel.CONTRACT_TERMS_FIXED).configure(
                entity_slug=setup["entity_model"].slug,
                customer_model=setup["customer_model"],
            )

        with self.assertRaises(Http404):
            self.configure_estimate(
                setup,
                entity_input=setup["entity_model"].slug,
                user_model=self.unrelated_user,
            )

        with self.assertRaises(Http404):
            self.configure_estimate(
                setup,
                entity_input=setup["entity_model"].uuid,
                user_model=self.unrelated_user,
            )

    def test_configure_rejects_customer_from_another_entity(self):
        setup = self.create_entity_setup(name="API Estimate Configure Customer Entity")
        other_setup = self.create_entity_setup(name="API Estimate Configure Other Customer Entity")

        with self.assertRaises(EstimateModelValidationError):
            self.configure_estimate(setup, customer_model=other_setup["customer_model"])

        self.assertFalse(
            EstimateModel.objects.filter(
                entity=setup["entity_model"],
                customer=other_setup["customer_model"],
            ).exists()
        )

    def test_configure_respects_explicit_draft_date(self):
        setup = self.create_entity_setup(name="API Estimate Configure Draft Date Entity")

        estimate_model = self.configure_estimate(setup, date_draft=date(2025, 12, 31))

        self.assertEqual(estimate_model.date_draft, date(2025, 12, 31))
        self.assertIn("-2025-", estimate_model.estimate_number)

    def test_configure_commit_false_generates_number_and_state_without_persisting_estimate(self):
        setup = self.create_entity_setup(name="API Estimate Configure Commit False Entity")

        estimate_model = self.configure_estimate(setup, commit=False)

        self.assertTrue(estimate_model.is_configured())
        self.assertTrue(estimate_model.estimate_number)
        self.assertEqual(estimate_model.date_draft, date(2026, 1, 15))
        self.assertFalse(EstimateModel.objects.filter(uuid=estimate_model.uuid).exists())

        state_model = EntityStateModel.objects.get(
            entity_model=setup["entity_model"],
            entity_unit__isnull=True,
            fiscal_year=2026,
            key=EntityStateModel.KEY_ESTIMATE,
        )
        self.assertEqual(state_model.sequence, 1)
        self.assert_number_ends_with_sequence(estimate_model.estimate_number, 1)

    def test_generate_estimate_number_commit_false_and_true_behaviors(self):
        setup = self.create_entity_setup(name="API Estimate Configure Number Entity")
        manual_estimate = EstimateModel.objects.create(
            entity=setup["entity_model"],
            customer=setup["customer_model"],
            terms=EstimateModel.CONTRACT_TERMS_FIXED,
            title="API Manual Number Estimate",
            date_draft=date(2026, 1, 15),
            estimate_number="manual-est-1",
        )
        manual_estimate.estimate_number = ""

        self.assertTrue(manual_estimate.can_generate_estimate_number())
        generated_number = manual_estimate.generate_estimate_number(commit=False)

        self.assertTrue(generated_number)
        self.assertEqual(
            EstimateModel.objects.get(uuid=manual_estimate.uuid).estimate_number,
            "manual-est-1",
        )

        persisted_estimate = EstimateModel.objects.create(
            entity=setup["entity_model"],
            customer=setup["customer_model"],
            terms=EstimateModel.CONTRACT_TERMS_FIXED,
            title="API Persisted Number Estimate",
            date_draft=date(2026, 1, 15),
            estimate_number="manual-est-2",
        )
        persisted_estimate.estimate_number = ""

        persisted_number = persisted_estimate.generate_estimate_number(commit=True)

        self.assertTrue(persisted_number)
        self.assertEqual(
            EstimateModel.objects.get(uuid=persisted_estimate.uuid).estimate_number,
            persisted_number,
        )

    def test_get_item_model_qs_returns_estimate_eligible_items(self):
        setup = self.create_entity_setup(name="API Estimate Configure Item Query Entity")
        estimate_model = self.configure_estimate(setup)

        item_qs = estimate_model.get_item_model_qs()

        self.assertTrue(item_qs.filter(uuid=setup["service_item"].uuid).exists())
        self.assertTrue(item_qs.filter(uuid=setup["product_item"].uuid).exists())
        self.assertFalse(item_qs.filter(uuid=setup["expense_item"].uuid).exists())

    def test_migrate_itemtxs_replace_and_append_create_estimate_items_and_update_amounts(self):
        setup = self.create_entity_setup(name="API Estimate Configure Item Migration Entity")
        estimate_model = self.configure_estimate(setup)

        estimate_model, itemtxs_batch = self.migrate_service_item(estimate_model, setup)

        self.assertEqual(len(itemtxs_batch), 1)
        item_tx = ItemTransactionModel.objects.get(ce_model=estimate_model)
        self.assertEqual(item_tx.item_model_id, setup["service_item"].uuid)
        self.assertEqual(item_tx.ce_quantity, Decimal("2.00"))
        self.assertEqual(item_tx.ce_unit_cost_estimate, Decimal("50.00"))
        self.assertEqual(item_tx.ce_unit_revenue_estimate, Decimal("75.00"))
        self.assertEqual(item_tx.ce_cost_estimate, Decimal("100.00"))
        self.assertEqual(item_tx.ce_revenue_estimate, Decimal("150.00"))
        self.assertEqual(estimate_model.revenue_estimate, Decimal("150.00"))
        self.assertEqual(estimate_model.labor_estimate, Decimal("100.00"))

        estimate_model, appended_batch = self.migrate_product_item(estimate_model, setup)

        self.assertEqual(len(appended_batch), 2)
        self.assertEqual(ItemTransactionModel.objects.filter(ce_model=estimate_model).count(), 2)
        self.assertEqual(estimate_model.revenue_estimate, Decimal("185.00"))
        self.assertEqual(estimate_model.material_estimate, Decimal("20.00"))

        estimate_model, replacement_batch = self.migrate_service_item(
            estimate_model,
            setup,
            quantity="1.00",
            unit_cost="25.00",
            unit_revenue="40.00",
        )

        self.assertEqual(len(replacement_batch), 1)
        self.assertEqual(ItemTransactionModel.objects.filter(ce_model=estimate_model).count(), 1)
        self.assertEqual(estimate_model.revenue_estimate, Decimal("40.00"))
        self.assertEqual(estimate_model.labor_estimate, Decimal("25.00"))
        self.assertEqual(estimate_model.material_estimate, Decimal("0.00"))

    def test_validate_itemtxs_qs_rejects_transactions_from_another_estimate(self):
        setup = self.create_entity_setup(name="API Estimate Configure Validate ItemTx Entity")
        estimate_model = self.configure_estimate(setup)
        other_estimate_model = self.configure_estimate(setup, title="API Other Estimate")
        other_estimate_model, _itemtxs_batch = self.migrate_service_item(other_estimate_model, setup)
        other_itemtxs = ItemTransactionModel.objects.filter(ce_model=other_estimate_model)

        with self.assertRaises(EstimateModelValidationError):
            estimate_model.validate_itemtxs_qs(other_itemtxs)

        with self.assertRaises(EstimateModelValidationError):
            estimate_model.validate_item_transaction_qs(other_itemtxs)

    def test_get_itemtxs_data_returns_estimate_items_without_aggregate_payload(self):
        setup = self.create_entity_setup(name="API Estimate Configure Item Data Entity")
        estimate_model = self.configure_estimate(setup)
        estimate_model, _itemtxs_batch = self.migrate_service_item(estimate_model, setup)

        itemtxs_qs, itemtxs_data = estimate_model.get_itemtxs_data()

        self.assertEqual(itemtxs_qs.count(), 1)
        self.assertIsNone(itemtxs_data)
        self.assertEqual(itemtxs_qs.get().ce_revenue_estimate, Decimal("150.00"))
