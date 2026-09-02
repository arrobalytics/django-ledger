"""
High-level API behavior tests for EntityModel default CoA helpers.

These tests focus on EntityModel's public default Chart of Accounts helper
behavior without re-testing CoA tree internals.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH
from django_ledger.models.entity import EntityModel, EntityModelValidationError


class EntityDefaultCoAHelpersAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_entity_default_coa_user",
            email="api-entity-default-coa-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Entity Default CoA Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def test_entity_without_default_coa_reports_no_default(self):
        entity_model = self.create_entity(name="API Entity Without Default CoA")

        self.assertFalse(entity_model.has_default_coa())
        self.assertIsNone(entity_model.get_default_coa(raise_exception=False))

        with self.assertRaises(EntityModelValidationError):
            entity_model.get_default_coa()

    def test_entity_with_assigned_default_coa_reports_default(self):
        entity_model = self.create_entity(name="API Entity With Default CoA")

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Assigned Default CoA",
            commit=True,
            assign_as_default=True,
        )

        entity_model.refresh_from_db()
        coa_model.refresh_from_db()

        self.assertTrue(entity_model.has_default_coa())
        self.assertEqual(entity_model.default_coa_id, coa_model.uuid)
        self.assertEqual(entity_model.get_default_coa(), coa_model)
        self.assertTrue(coa_model.is_default())

    def test_non_default_coa_creation_does_not_change_default_helper_result(self):
        entity_model = self.create_entity(name="API Entity Preserve Default CoA")
        first_coa = entity_model.create_chart_of_accounts(
            coa_name="API First Default CoA",
            commit=True,
            assign_as_default=True,
        )

        second_coa = entity_model.create_chart_of_accounts(
            coa_name="API Second Non Default CoA",
            commit=True,
            assign_as_default=False,
        )

        entity_model.refresh_from_db()
        first_coa.refresh_from_db()
        second_coa.refresh_from_db()

        self.assertTrue(entity_model.has_default_coa())
        self.assertEqual(entity_model.default_coa_id, first_coa.uuid)
        self.assertEqual(entity_model.get_default_coa(), first_coa)
        self.assertTrue(first_coa.is_default())
        self.assertFalse(second_coa.is_default())

    def test_get_default_coa_returns_current_default_after_default_changes(self):
        entity_model = self.create_entity(name="API Entity Switch Default CoA")
        first_coa = entity_model.create_chart_of_accounts(
            coa_name="API Switch First CoA",
            commit=True,
            assign_as_default=True,
        )
        second_coa = entity_model.create_chart_of_accounts(
            coa_name="API Switch Second CoA",
            commit=True,
            assign_as_default=False,
        )

        second_coa.mark_as_default(commit=True)

        entity_model.refresh_from_db()
        first_coa.refresh_from_db()
        second_coa.refresh_from_db()

        self.assertTrue(entity_model.has_default_coa())
        self.assertEqual(entity_model.get_default_coa(), second_coa)
        self.assertFalse(first_coa.is_default())
        self.assertTrue(second_coa.is_default())

    def test_default_coa_helpers_work_after_default_coa_population(self):
        entity_model = self.create_entity(name="API Entity Populated Default CoA")

        entity_model.populate_default_coa(activate_accounts=True)
        entity_model.refresh_from_db()

        coa_model = entity_model.get_default_coa()
        cash_account = entity_model.get_default_coa_accounts(active=True).get(code="1010")

        self.assertTrue(entity_model.has_default_coa())
        self.assertTrue(coa_model.is_configured())
        self.assertEqual(cash_account.role, ASSET_CA_CASH)
        self.assertEqual(cash_account.coa_model_id, coa_model.uuid)
