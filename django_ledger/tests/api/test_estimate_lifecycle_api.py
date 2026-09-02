"""
High-level API tests for EstimateModel lifecycle transitions.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_INVENTORY,
    COGS,
    INCOME_OPERATIONAL,
)
from django_ledger.models import EstimateModel, ItemTransactionModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.estimate import EstimateModelValidationError


class EstimateLifecycleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_estimate_lifecycle_user",
            email="api-estimate-lifecycle-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Estimate Lifecycle Entity"):
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
        uom_model = entity_model.create_uom(
            name=f"Unit {str(entity_model.uuid)[:8]}",
            unit_abbr=f"e-{str(entity_model.uuid)[:6]}",
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
        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "customer_model": customer_model,
            "service_item": service_item,
        }

    def create_estimate(self, setup, *, date_draft=date(2025, 1, 15), title="API Estimate Lifecycle Contract"):
        estimate_model = setup["entity_model"].create_estimate(
            estimate_title=title,
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=setup["customer_model"],
            date_draft=date_draft,
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def migrate_service_item(self, estimate_model, setup, *, quantity="1.00", unit_cost="100.00", unit_revenue="150.00"):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        unit_revenue = Decimal(unit_revenue)
        estimate_model.migrate_itemtxs(
            itemtxs={
                setup["service_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "unit_revenue": unit_revenue,
                    "total_amount": quantity * unit_revenue,
                }
            },
            operation=EstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def make_review_estimate(self, setup):
        estimate_model = self.migrate_service_item(self.create_estimate(setup), setup)
        estimate_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        estimate_model.refresh_from_db()
        return estimate_model

    def make_approved_estimate(self, setup):
        estimate_model = self.make_review_estimate(setup)
        estimate_model.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))
        estimate_model.refresh_from_db()
        return estimate_model

    def make_completed_estimate(self, setup):
        estimate_model = self.make_approved_estimate(setup)
        estimate_model.mark_as_completed(commit=True, date_completed=date(2025, 1, 18))
        estimate_model.refresh_from_db()
        return estimate_model

    def test_valid_status_transitions_set_dates_and_contract_flags(self):
        setup = self.create_entity_setup(name="API Estimate Lifecycle Valid Entity")
        estimate_model = self.migrate_service_item(self.create_estimate(setup), setup)

        estimate_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        estimate_model.refresh_from_db()
        self.assertTrue(estimate_model.is_review())
        self.assertFalse(estimate_model.is_contract())
        self.assertEqual(estimate_model.date_in_review, date(2025, 1, 16))

        estimate_model.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))
        estimate_model.refresh_from_db()
        self.assertTrue(estimate_model.is_approved())
        self.assertTrue(estimate_model.is_contract())
        self.assertEqual(estimate_model.date_approved, date(2025, 1, 17))

        estimate_model.mark_as_completed(commit=True, date_completed=date(2025, 1, 18))
        estimate_model.refresh_from_db()
        self.assertTrue(estimate_model.is_completed())
        self.assertTrue(estimate_model.is_contract())
        self.assertEqual(estimate_model.date_completed, date(2025, 1, 18))

    def test_cancel_and_void_transitions_set_terminal_status_dates(self):
        setup = self.create_entity_setup(name="API Estimate Lifecycle Terminal Entity")

        draft_estimate = self.create_estimate(setup)
        draft_estimate.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))
        draft_estimate.refresh_from_db()
        self.assertTrue(draft_estimate.is_canceled())
        self.assertEqual(draft_estimate.date_canceled, date(2025, 1, 20))

        review_estimate = self.make_review_estimate(setup)
        review_estimate.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 21))
        review_estimate.refresh_from_db()
        self.assertTrue(review_estimate.is_canceled())
        self.assertEqual(review_estimate.date_canceled, date(2025, 1, 21))

        approved_estimate = self.make_approved_estimate(setup)
        approved_estimate.mark_as_void(commit=True, date_void=date(2025, 1, 22))
        approved_estimate.refresh_from_db()
        self.assertTrue(approved_estimate.is_void())
        self.assertEqual(approved_estimate.date_void, date(2025, 1, 22))

    def test_can_predicates_reflect_status_transitions(self):
        setup = self.create_entity_setup(name="API Estimate Lifecycle Predicate Entity")

        draft_estimate = self.create_estimate(setup)
        self.assertFalse(draft_estimate.can_draft())
        self.assertTrue(draft_estimate.can_review())
        self.assertFalse(draft_estimate.can_approve())
        self.assertFalse(draft_estimate.can_complete())
        self.assertTrue(draft_estimate.can_cancel())
        self.assertFalse(draft_estimate.can_void())
        self.assertTrue(draft_estimate.can_update_items())
        self.assertFalse(draft_estimate.can_bind())

        review_estimate = self.make_review_estimate(setup)
        self.assertTrue(review_estimate.can_draft())
        self.assertFalse(review_estimate.can_review())
        self.assertTrue(review_estimate.can_approve())
        self.assertFalse(review_estimate.can_complete())
        self.assertTrue(review_estimate.can_cancel())
        self.assertFalse(review_estimate.can_void())
        self.assertFalse(review_estimate.can_update_items())
        self.assertFalse(review_estimate.can_bind())

        approved_estimate = self.make_approved_estimate(setup)
        self.assertFalse(approved_estimate.can_draft())
        self.assertFalse(approved_estimate.can_approve())
        self.assertTrue(approved_estimate.can_complete())
        self.assertFalse(approved_estimate.can_cancel())
        self.assertTrue(approved_estimate.can_void())
        self.assertFalse(approved_estimate.can_update_items())
        self.assertTrue(approved_estimate.can_bind())

        completed_estimate = self.make_completed_estimate(setup)
        self.assertFalse(completed_estimate.can_complete())
        self.assertFalse(completed_estimate.can_cancel())
        self.assertFalse(completed_estimate.can_void())
        self.assertFalse(completed_estimate.can_update_items())
        self.assertFalse(completed_estimate.can_bind())

    def test_commit_false_transitions_mutate_in_memory_without_persisting(self):
        setup = self.create_entity_setup(name="API Estimate Lifecycle Commit False Entity")
        estimate_model = self.migrate_service_item(self.create_estimate(setup), setup)

        estimate_model.mark_as_review(commit=False, date_in_review=date(2025, 1, 16))
        self.assertTrue(estimate_model.is_review())
        self.assertEqual(estimate_model.date_in_review, date(2025, 1, 16))
        db_estimate = EstimateModel.objects.get(uuid=estimate_model.uuid)
        self.assertTrue(db_estimate.is_draft())
        self.assertIsNone(db_estimate.date_in_review)

        estimate_model.refresh_from_db()
        estimate_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        estimate_model.refresh_from_db()
        estimate_model.mark_as_approved(commit=False, date_approved=date(2025, 1, 17))
        self.assertTrue(estimate_model.is_approved())
        self.assertEqual(estimate_model.date_approved, date(2025, 1, 17))
        db_estimate = EstimateModel.objects.get(uuid=estimate_model.uuid)
        self.assertTrue(db_estimate.is_review())
        self.assertIsNone(db_estimate.date_approved)

    def test_review_requires_items_cost_and_revenue(self):
        setup = self.create_entity_setup(name="API Estimate Lifecycle Review Requirement Entity")
        estimate_model = self.create_estimate(setup)

        with self.assertRaises(EstimateModelValidationError):
            estimate_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

        self.assertFalse(ItemTransactionModel.objects.filter(ce_model=estimate_model).exists())

        zero_cost_estimate = self.migrate_service_item(
            self.create_estimate(setup, title="API Zero Cost Estimate"),
            setup,
            unit_cost="0.00",
            unit_revenue="150.00",
        )
        with self.assertRaises(EstimateModelValidationError):
            zero_cost_estimate.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

        zero_revenue_estimate = self.migrate_service_item(
            self.create_estimate(setup, title="API Zero Revenue Estimate"),
            setup,
            unit_cost="100.00",
            unit_revenue="0.00",
        )
        with self.assertRaises(EstimateModelValidationError):
            zero_revenue_estimate.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

    def test_invalid_transitions_raise_validation_errors_or_noop_when_suppressed(self):
        setup = self.create_entity_setup(name="API Estimate Lifecycle Invalid Entity")
        draft_estimate = self.create_estimate(setup)

        with self.assertRaises(EstimateModelValidationError):
            draft_estimate.mark_as_completed(commit=True, date_completed=date(2025, 1, 18))

        result = draft_estimate.mark_as_completed(
            commit=True,
            date_completed=date(2025, 1, 18),
            raise_exception=False,
        )
        self.assertIsNone(result)
        draft_estimate.refresh_from_db()
        self.assertTrue(draft_estimate.is_draft())

        completed_estimate = self.make_completed_estimate(setup)
        with self.assertRaises(EstimateModelValidationError):
            completed_estimate.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 19))
        with self.assertRaises(EstimateModelValidationError):
            completed_estimate.mark_as_void(commit=True, date_void=date(2025, 1, 19))

        canceled_estimate = self.create_estimate(setup)
        canceled_estimate.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))
        with self.assertRaises(ValidationError):
            canceled_estimate.mark_as_review(commit=True, date_in_review=date(2025, 1, 21))

        void_estimate = self.make_approved_estimate(setup)
        void_estimate.mark_as_void(commit=True, date_void=date(2025, 1, 22))
        with self.assertRaises(EstimateModelValidationError):
            void_estimate.mark_as_completed(commit=True, date_completed=date(2025, 1, 23))
