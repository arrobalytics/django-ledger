"""
Smoke-level compatibility tests for the deprecated entity_slug shim.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import AccountModel
from django_ledger.models.accounts import AccountModelValidationError
from django_ledger.models.entity import EntityModel


class DeprecatedEntitySlugAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_deprecated_entity_slug_admin",
            email="api-deprecated-entity-slug-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Deprecated Entity Slug Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        account_model = coa_model.create_account(
            code="1010",
            name=f"{name} Cash",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )
        return entity_model, account_model

    def test_entity_slug_kwarg_warns_and_maps_when_deprecated_behavior_enabled(self):
        entity_model, account_model = self.create_entity_setup(
            name="API Deprecated Entity Slug Enabled"
        )

        with patch("django_ledger.models.deprecations.DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR", True):
            with self.assertWarns(DeprecationWarning):
                account_qs = AccountModel.objects.for_entity(entity_slug=entity_model.slug)

        self.assertTrue(account_qs.filter(uuid=account_model.uuid).exists())

    def test_entity_slug_kwarg_warns_and_uses_current_disabled_behavior(self):
        entity_model, _account_model = self.create_entity_setup(
            name="API Deprecated Entity Slug Disabled"
        )

        with self.assertWarns(DeprecationWarning):
            with self.assertRaises(AccountModelValidationError):
                AccountModel.objects.for_entity(entity_slug=entity_model.slug)

    def test_entity_model_and_entity_slug_conflict_is_rejected(self):
        entity_model, _account_model = self.create_entity_setup(
            name="API Deprecated Entity Slug Conflict"
        )

        with self.assertWarns(DeprecationWarning):
            with self.assertRaises(ValueError):
                AccountModel.objects.for_entity(
                    entity_model=entity_model,
                    entity_slug=entity_model.slug,
                )
