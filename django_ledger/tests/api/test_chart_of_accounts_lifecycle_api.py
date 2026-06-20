"""
High-level API behavior tests for ChartOfAccountModel lifecycle helpers.

These tests cover default/active state transitions without URL or queryset
assertions.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.chart_of_accounts import ChartOfAccountsModelValidationError
from django_ledger.models.entity import EntityModel


class ChartOfAccountsLifecycleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_coa_lifecycle_user",
            email="api-coa-lifecycle-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API CoA Lifecycle Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_coa(self, entity_model, *, name, assign_as_default=False):
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=name,
            commit=True,
            assign_as_default=assign_as_default,
        )
        entity_model.refresh_from_db()
        return coa_model

    def create_entity_with_two_coas(self, *, name="API CoA Lifecycle Entity"):
        entity_model = self.create_entity(name=name)
        default_coa = self.create_coa(
            entity_model,
            name=f"{name} Default CoA",
            assign_as_default=True,
        )
        secondary_coa = self.create_coa(
            entity_model,
            name=f"{name} Secondary CoA",
            assign_as_default=False,
        )
        return entity_model, default_coa, secondary_coa

    def test_mark_as_default_commit_true_sets_entity_default_coa(self):
        entity_model, default_coa, secondary_coa = self.create_entity_with_two_coas(
            name="API CoA Mark Default Entity",
        )

        secondary_coa.mark_as_default(commit=True)

        entity_model.refresh_from_db()
        default_coa.refresh_from_db()
        secondary_coa.refresh_from_db()

        self.assertEqual(entity_model.default_coa_id, secondary_coa.uuid)
        self.assertFalse(default_coa.is_default())
        self.assertTrue(secondary_coa.is_default())

    def test_default_coa_reports_is_default_true(self):
        _entity_model, default_coa, secondary_coa = self.create_entity_with_two_coas(
            name="API CoA Is Default Entity",
        )

        self.assertTrue(default_coa.is_default())
        self.assertFalse(secondary_coa.is_default())

    def test_inactive_coa_cannot_be_marked_as_default(self):
        entity_model, default_coa, secondary_coa = self.create_entity_with_two_coas(
            name="API CoA Inactive Default Entity",
        )
        secondary_coa.mark_as_inactive(commit=True)
        secondary_coa.refresh_from_db()

        with self.assertRaises(ChartOfAccountsModelValidationError):
            secondary_coa.mark_as_default(commit=True, raise_exception=True)

        entity_model.refresh_from_db()
        self.assertEqual(entity_model.default_coa_id, default_coa.uuid)
        self.assertFalse(secondary_coa.is_default())

    def test_default_coa_cannot_be_deactivated(self):
        _entity_model, default_coa, _secondary_coa = self.create_entity_with_two_coas(
            name="API CoA Default Deactivate Entity",
        )

        with self.assertRaises(ChartOfAccountsModelValidationError):
            default_coa.mark_as_inactive(commit=True)

        default_coa.refresh_from_db()
        self.assertTrue(default_coa.active)
        self.assertTrue(default_coa.is_default())

    def test_non_default_active_coa_can_be_marked_inactive(self):
        _entity_model, _default_coa, secondary_coa = self.create_entity_with_two_coas(
            name="API CoA Mark Inactive Entity",
        )

        secondary_coa.mark_as_inactive(commit=True)

        secondary_coa.refresh_from_db()
        self.assertFalse(secondary_coa.active)

    def test_inactive_non_default_coa_can_be_marked_active(self):
        _entity_model, _default_coa, secondary_coa = self.create_entity_with_two_coas(
            name="API CoA Mark Active Entity",
        )
        secondary_coa.mark_as_inactive(commit=True)
        secondary_coa.refresh_from_db()

        secondary_coa.mark_as_active(commit=True)

        secondary_coa.refresh_from_db()
        self.assertTrue(secondary_coa.active)

    def test_lifecycle_predicates_reflect_default_and_active_state(self):
        _entity_model, default_coa, secondary_coa = self.create_entity_with_two_coas(
            name="API CoA Predicate Entity",
        )

        self.assertFalse(default_coa.can_mark_as_default())
        self.assertFalse(default_coa.can_activate())
        self.assertFalse(default_coa.can_deactivate())

        self.assertTrue(secondary_coa.can_mark_as_default())
        self.assertFalse(secondary_coa.can_activate())
        self.assertTrue(secondary_coa.can_deactivate())

        secondary_coa.mark_as_inactive(commit=True)
        secondary_coa.refresh_from_db()

        self.assertFalse(secondary_coa.can_mark_as_default())
        self.assertTrue(secondary_coa.can_activate())
        self.assertFalse(secondary_coa.can_deactivate())

    def test_invalid_lifecycle_calls_without_raise_exception_are_noops(self):
        entity_model, default_coa, secondary_coa = self.create_entity_with_two_coas(
            name="API CoA Noop Entity",
        )
        secondary_coa.mark_as_inactive(commit=True)
        secondary_coa.refresh_from_db()

        default_coa.mark_as_default(commit=True, raise_exception=False)
        secondary_coa.mark_as_default(commit=True, raise_exception=False)
        secondary_coa.mark_as_inactive(commit=True, raise_exception=False)

        entity_model.refresh_from_db()
        secondary_coa.refresh_from_db()

        self.assertEqual(entity_model.default_coa_id, default_coa.uuid)
        self.assertFalse(secondary_coa.active)
