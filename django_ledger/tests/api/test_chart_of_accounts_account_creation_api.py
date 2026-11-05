"""
High-level API behavior tests for ChartOfAccountModel account creation helpers.

These tests cover public account insertion behavior without asserting exact
tree path strings.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    DEBIT,
    EXPENSE_OPERATIONAL,
    ROOT_ASSETS,
    ROOT_EXPENSES,
)
from django_ledger.models import AccountModel
from django_ledger.models.chart_of_accounts import ChartOfAccountsModelValidationError
from django_ledger.models.entity import EntityModel


class ChartOfAccountsAccountCreationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_coa_account_creation_user",
            email="api-coa-account-creation-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API CoA Account Creation Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_coa(self, *, name="API CoA Account Creation CoA"):
        entity_model = self.create_entity(name=f"{name} Entity")
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=name,
            commit=True,
            assign_as_default=True,
        )
        entity_model.refresh_from_db()
        return entity_model, coa_model

    def assert_account_has_ancestor_role(self, account_model, role):
        ancestor_roles = {ancestor.role for ancestor in account_model.get_ancestors()}
        self.assertIn(role, ancestor_roles)

    def test_create_account_creates_non_root_account_attached_to_same_coa(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Create Cash")

        account_model = coa_model.create_account(
            code="1010",
            name="API Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
        )

        account_model.refresh_from_db()

        self.assertEqual(account_model.coa_model_id, coa_model.uuid)
        self.assertFalse(account_model.is_root_account())
        self.assertTrue(account_model.active)
        self.assertTrue(coa_model.get_non_root_coa_accounts_qs().filter(uuid=account_model.uuid).exists())

    def test_create_account_inserts_asset_account_under_assets_root(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Asset Root")

        account_model = coa_model.create_account(
            code="1010",
            name="API Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
        )

        self.assert_account_has_ancestor_role(account_model, ROOT_ASSETS)

    def test_create_account_inserts_expense_account_under_expenses_root(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Expense Root")

        account_model = coa_model.create_account(
            code="6010",
            name="API Expense Account",
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=True,
        )

        self.assert_account_has_ancestor_role(account_model, ROOT_EXPENSES)

    def test_insert_account_rejects_account_tied_to_different_coa(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Insert Target")
        _other_entity, other_coa = self.create_coa(name="API CoA Insert Other")
        account_model = AccountModel(
            code="1010",
            name="API Wrong CoA Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            coa_model=other_coa,
        )

        with self.assertRaises(ChartOfAccountsModelValidationError):
            coa_model.insert_account(account_model)

    def test_get_account_root_node_rejects_root_accounts(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Root Reject")
        root_account = coa_model.get_coa_root_node()

        with self.assertRaises(ChartOfAccountsModelValidationError):
            coa_model.get_account_root_node(root_account)

    def test_create_account_can_mark_role_default(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Role Default")

        account_model = coa_model.create_account(
            code="1010",
            name="API Default Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )

        account_model.refresh_from_db()
        self.assertTrue(account_model.role_default)

    def test_second_role_default_for_same_role_raises_without_force(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Duplicate Default")
        first_default = coa_model.create_account(
            code="1010",
            name="API First Default Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )

        with self.assertRaises(ChartOfAccountsModelValidationError):
            coa_model.create_account(
                code="1020",
                name="API Second Default Cash Account",
                role=ASSET_CA_CASH,
                balance_type=DEBIT,
                active=True,
                is_role_default=True,
            )

        first_default.refresh_from_db()
        self.assertTrue(first_default.role_default)
        self.assertFalse(coa_model.get_coa_accounts(active_only=False).filter(code="1020").exists())

    def test_force_role_default_clears_old_default_and_sets_new_default(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Force Default")
        first_default = coa_model.create_account(
            code="1010",
            name="API First Default Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )

        second_default = coa_model.create_account(
            code="1020",
            name="API Second Default Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
            force_role_default=True,
        )

        first_default.refresh_from_db()
        second_default.refresh_from_db()

        self.assertIsNone(first_default.role_default)
        self.assertTrue(second_default.role_default)
