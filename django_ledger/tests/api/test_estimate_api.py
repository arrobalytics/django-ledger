"""
High-level API behavior tests for EstimateModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import EstimateModel, ItemTransactionModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel


class EstimateHighLevelAPITest(TestCase):
    """
    High-level behavior tests for EstimateModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic estimate/customer/item lifecycle
    invariants that should remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_estimate_contract_user",
            email="api-estimate-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_with_estimate_setup(self, *, name="API Estimate Contract Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Estimate Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        inventory_account = coa_model.create_account(
            code="1510",
            name="API Estimate Inventory Account",
            role="asset_ca_inv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        cogs_account = coa_model.create_account(
            code="5010",
            name="API Estimate COGS Account",
            role="cogs_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        earnings_account = coa_model.create_account(
            code="4010",
            name="API Estimate Earnings Account",
            role="in_operational",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        uom_model = entity_model.create_uom(
            name="API Estimate Unit",
            unit_abbr="api-est",
            active=True,
            commit=True,
        )

        customer_model = CustomerModel(
            customer_name="API Estimate Customer",
            entity_model=entity_model,
            description="API Estimate Customer description",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()

        service_item = entity_model.create_item_service(
            name="API Estimate Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )

        material_item = entity_model.create_item_product(
            name="API Estimate Material Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "inventory_account": inventory_account,
            "cogs_account": cogs_account,
            "earnings_account": earnings_account,
            "uom_model": uom_model,
            "customer_model": customer_model,
            "service_item": service_item,
            "material_item": material_item,
        }

    def create_configured_estimate(self, setup):
        estimate_model = EstimateModel(
            terms=EstimateModel.CONTRACT_TERMS_FIXED,
        )
        estimate_model.configure(
            entity_slug=setup["entity_model"],
            customer_model=setup["customer_model"],
            user_model=self.user,
            date_draft=date(2026, 1, 15),
            estimate_title="API Estimate Contract",
            commit=True,
        )
        return estimate_model

    def migrate_service_item(
        self,
        estimate_model,
        setup,
        *,
        quantity="2.00",
        unit_cost="30.00",
        unit_revenue="75.00",
    ):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        unit_revenue = Decimal(unit_revenue)

        itemtxs = {
            setup["service_item"].item_number: {
                "quantity": quantity,
                "unit_cost": unit_cost,
                "unit_revenue": unit_revenue,
                "total_amount": quantity * unit_revenue,
            }
        }

        estimate_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=EstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )

        estimate_model.refresh_from_db()
        return estimate_model

    def migrate_material_item(
        self,
        estimate_model,
        setup,
        *,
        quantity="3.00",
        unit_cost="20.00",
        unit_revenue="50.00",
    ):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        unit_revenue = Decimal(unit_revenue)

        itemtxs = {
            setup["material_item"].item_number: {
                "quantity": quantity,
                "unit_cost": unit_cost,
                "unit_revenue": unit_revenue,
                "total_amount": quantity * unit_revenue,
            }
        }

        estimate_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=EstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )

        estimate_model.refresh_from_db()
        return estimate_model

    def test_estimate_configure_creates_draft_estimate_under_entity_and_customer(self):
        setup = self.create_entity_with_estimate_setup()

        estimate_model = self.create_configured_estimate(setup)

        self.assertIsInstance(estimate_model, EstimateModel)
        self.assertIsNotNone(estimate_model.uuid)
        self.assertEqual(estimate_model.entity_id, setup["entity_model"].uuid)
        self.assertEqual(estimate_model.customer_id, setup["customer_model"].uuid)
        self.assertEqual(estimate_model.title, "API Estimate Contract")
        self.assertTrue(estimate_model.is_draft())
        self.assertFalse(estimate_model.is_approved())
        self.assertTrue(estimate_model.estimate_number)

    def test_estimate_item_migration_creates_item_transaction(self):
        setup = self.create_entity_with_estimate_setup()
        estimate_model = self.create_configured_estimate(setup)

        self.migrate_service_item(estimate_model, setup)

        item_txs = ItemTransactionModel.objects.filter(ce_model=estimate_model)

        self.assertEqual(item_txs.count(), 1)

        item_tx = item_txs.get()

        self.assertEqual(item_tx.item_model_id, setup["service_item"].uuid)
        self.assertEqual(item_tx.ce_quantity, Decimal("2.00"))
        self.assertEqual(item_tx.ce_unit_cost_estimate, Decimal("30.00"))
        self.assertEqual(item_tx.ce_unit_revenue_estimate, Decimal("75.00"))
        self.assertEqual(item_tx.ce_cost_estimate, Decimal("60.00"))
        self.assertEqual(item_tx.ce_revenue_estimate, Decimal("150.00"))

    def test_estimate_item_migration_updates_revenue_and_labor_estimates(self):
        setup = self.create_entity_with_estimate_setup()
        estimate_model = self.create_configured_estimate(setup)

        estimate_model = self.migrate_service_item(estimate_model, setup)

        self.assertEqual(estimate_model.revenue_estimate, Decimal("150.00"))
        self.assertEqual(estimate_model.labor_estimate, Decimal("60.00"))

    def test_estimate_item_migration_updates_material_estimate(self):
        setup = self.create_entity_with_estimate_setup()
        estimate_model = self.create_configured_estimate(setup)

        estimate_model = self.migrate_material_item(estimate_model, setup)

        self.assertEqual(estimate_model.revenue_estimate, Decimal("150.00"))
        self.assertEqual(estimate_model.material_estimate, Decimal("60.00"))

    def test_estimate_for_entity_queryset_limits_scope(self):
        setup = self.create_entity_with_estimate_setup(name="API Estimate Entity A")
        other_setup = self.create_entity_with_estimate_setup(name="API Estimate Entity B")

        estimate_model = self.create_configured_estimate(setup)
        other_estimate_model = self.create_configured_estimate(other_setup)

        scoped_qs = EstimateModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(scoped_qs.filter(uuid=estimate_model.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_estimate_model.uuid).exists())

    def test_estimate_can_move_from_draft_to_review(self):
        setup = self.create_entity_with_estimate_setup()
        estimate_model = self.create_configured_estimate(setup)
        estimate_model = self.migrate_service_item(estimate_model, setup)

        estimate_model.mark_as_review(commit=True)
        estimate_model.refresh_from_db()

        self.assertTrue(estimate_model.is_review())
        self.assertFalse(estimate_model.is_draft())

    def test_estimate_can_move_from_review_to_approved(self):
        setup = self.create_entity_with_estimate_setup()
        estimate_model = self.create_configured_estimate(setup)
        estimate_model = self.migrate_service_item(estimate_model, setup)

        estimate_model.mark_as_review(commit=True)
        estimate_model.refresh_from_db()

        estimate_model.mark_as_approved(commit=True)
        estimate_model.refresh_from_db()

        self.assertTrue(estimate_model.is_approved())
        self.assertFalse(estimate_model.is_draft())

    def test_approved_estimate_can_be_marked_completed(self):
        setup = self.create_entity_with_estimate_setup()
        estimate_model = self.create_configured_estimate(setup)
        estimate_model = self.migrate_service_item(estimate_model, setup)

        estimate_model.mark_as_review(commit=True)
        estimate_model.refresh_from_db()

        estimate_model.mark_as_approved(commit=True)
        estimate_model.refresh_from_db()

        estimate_model.mark_as_completed(commit=True)
        estimate_model.refresh_from_db()

        self.assertTrue(estimate_model.is_completed())
