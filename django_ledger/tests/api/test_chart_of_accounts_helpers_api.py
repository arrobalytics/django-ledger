"""
High-level API behavior tests for ChartOfAccountModel helper and URL methods.

These tests provide smoke coverage for public helper behavior without asserting
private tree internals.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT, EXPENSE_OPERATIONAL
from django_ledger.models import AccountModel, ChartOfAccountModel
from django_ledger.models.chart_of_accounts import ChartOfAccountsModelValidationError
from django_ledger.models.entity import EntityModel


class ChartOfAccountsHelpersAPITest(TestCase):
    COA_SCOPED_URL_HELPERS = (
        "mark_as_default_url",
        "mark_as_active_url",
        "mark_as_inactive_url",
        "get_absolute_url",
        "get_update_url",
        "get_account_list_url",
        "get_create_coa_account_url",
    )
    ENTITY_SCOPED_URL_HELPERS = (
        "get_coa_list_url",
        "get_coa_list_inactive_url",
        "get_coa_create_url",
    )

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_coa_helpers_user",
            email="api-coa-helpers-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API CoA Helpers Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_coa(self, *, name="API CoA Helpers CoA", assign_as_default=True):
        entity_model = self.create_entity(name=f"{name} Entity")
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=name,
            commit=True,
            assign_as_default=assign_as_default,
        )
        entity_model.refresh_from_db()
        return entity_model, coa_model

    def create_cash_account(self, coa_model, *, code="1010", name="API Cash Account"):
        return coa_model.create_account(
            code=code,
            name=name,
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
        )

    def create_expense_account(self, coa_model, *, code="6010", name="API Expense Account"):
        return coa_model.create_account(
            code=code,
            name=name,
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=True,
        )

    def test_generate_slug_assigns_entity_scoped_slug_and_preserves_existing_slug(self):
        entity_model = self.create_entity(name="API CoA Generate Slug Entity")
        coa_model = ChartOfAccountModel(name="API Direct Slug CoA", entity=entity_model)

        coa_model.generate_slug()
        original_slug = coa_model.slug

        self.assertTrue(original_slug.startswith("coa-"))
        self.assertIn(entity_model.slug[-5:], original_slug)

        coa_model.generate_slug()
        self.assertEqual(coa_model.slug, original_slug)

        with self.assertRaises(ChartOfAccountsModelValidationError):
            coa_model.generate_slug(raise_exception=True)

    def test_entity_slug_uses_manager_annotation_and_direct_instance_fallback(self):
        entity_model, coa_model = self.create_coa(name="API CoA Entity Slug")

        annotated_coa = ChartOfAccountModel.objects.get(uuid=coa_model.uuid)
        direct_coa = ChartOfAccountModel(
            name="API Direct Entity Slug CoA",
            entity=entity_model,
        )

        self.assertEqual(annotated_coa.entity_slug, entity_model.slug)
        self.assertEqual(direct_coa.entity_slug, entity_model.slug)

    def test_validate_account_model_qs_accepts_same_coa_and_rejects_invalid_inputs(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Validate Account QS")
        _other_entity, other_coa = self.create_coa(name="API CoA Other Validate Account QS")
        same_coa_account = self.create_cash_account(coa_model)
        other_coa_account = self.create_cash_account(other_coa)

        same_coa_qs = AccountModel.objects.filter(uuid=same_coa_account.uuid)
        other_coa_qs = AccountModel.objects.filter(uuid=other_coa_account.uuid)

        self.assertIsNone(coa_model.validate_account_model_qs(same_coa_qs))

        with self.assertRaises(ChartOfAccountsModelValidationError):
            coa_model.validate_account_model_qs(other_coa_qs)

        with self.assertRaises(ChartOfAccountsModelValidationError):
            coa_model.validate_account_model_qs([same_coa_account])

    def test_lock_all_accounts_and_unlock_all_accounts_update_non_root_accounts(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Lock Unlock")
        cash_account = self.create_cash_account(coa_model, code="1010")
        expense_account = self.create_expense_account(coa_model, code="6010")

        coa_model.lock_all_accounts()

        cash_account.refresh_from_db()
        expense_account.refresh_from_db()
        self.assertTrue(cash_account.locked)
        self.assertTrue(expense_account.locked)

        coa_model.unlock_all_accounts()

        cash_account.refresh_from_db()
        expense_account.refresh_from_db()
        self.assertFalse(cash_account.locked)
        self.assertFalse(expense_account.locked)

    def test_get_coa_account_tree_returns_non_empty_serialized_tree(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Account Tree")
        self.create_cash_account(coa_model)

        account_tree = coa_model.get_coa_account_tree()

        self.assertIsInstance(account_tree, list)
        self.assertGreater(len(account_tree), 0)
        self.assertIsInstance(account_tree[0], dict)

    def test_url_helpers_return_entity_and_coa_scoped_strings(self):
        entity_model, coa_model = self.create_coa(name="API CoA URL Helpers")
        annotated_coa = ChartOfAccountModel.objects.get(uuid=coa_model.uuid)

        for helper_name in self.COA_SCOPED_URL_HELPERS:
            with self.subTest(helper_name=helper_name):
                url = getattr(annotated_coa, helper_name)()

                self.assertIsInstance(url, str)
                self.assertTrue(url)
                self.assertIn(entity_model.slug, url)
                self.assertIn(coa_model.slug, url)

        for helper_name in self.ENTITY_SCOPED_URL_HELPERS:
            with self.subTest(helper_name=helper_name):
                url = getattr(annotated_coa, helper_name)()

                self.assertIsInstance(url, str)
                self.assertTrue(url)
                self.assertIn(entity_model.slug, url)
