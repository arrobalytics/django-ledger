"""
High-level API behavior tests for ChartOfAccountModel configuration helpers.

These tests cover root-account setup and public account query helpers without
asserting fragile tree path internals.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    DEBIT,
    EXPENSE_OPERATIONAL,
    ROOT_ASSETS,
    ROOT_CAPITAL,
    ROOT_COA,
    ROOT_COGS,
    ROOT_EXPENSES,
    ROOT_INCOME,
    ROOT_LIABILITIES,
)
from django_ledger.models.entity import EntityModel


class ChartOfAccountsConfigureAPITest(TestCase):
    EXPECTED_ROOT_ROLES = {
        ROOT_COA,
        ROOT_ASSETS,
        ROOT_LIABILITIES,
        ROOT_CAPITAL,
        ROOT_INCOME,
        ROOT_COGS,
        ROOT_EXPENSES,
    }

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_coa_configure_user",
            email="api-coa-configure-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API CoA Configure Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_coa(self, *, name="API CoA Configure CoA"):
        entity_model = self.create_entity(name=f"{name} Entity")
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=name,
            commit=True,
            assign_as_default=True,
        )
        entity_model.refresh_from_db()
        return entity_model, coa_model

    def test_saved_coa_is_configured_with_expected_root_accounts(self):
        _entity_model, coa_model = self.create_coa(
            name="API CoA Configured Root Accounts",
        )

        self.assertTrue(coa_model.is_configured())

        root_accounts = list(coa_model.get_coa_root_accounts_qs())
        root_roles = {account.role for account in root_accounts}

        self.assertEqual(root_roles, self.EXPECTED_ROOT_ROLES)

        for root_account in root_accounts:
            with self.subTest(role=root_account.role):
                self.assertTrue(root_account.is_root_account())
                self.assertFalse(root_account.active)
                self.assertTrue(root_account.locked)
                self.assertTrue(root_account.role_default)

    def test_get_coa_root_node_returns_coa_root_account(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Root Node")

        root_node = coa_model.get_coa_root_node()

        self.assertEqual(root_node.role, ROOT_COA)
        self.assertTrue(root_node.is_coa_root())
        self.assertEqual(root_node.coa_model_id, coa_model.uuid)

    def test_root_and_non_root_account_query_helpers_partition_accounts(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Root Partition")
        cash_account = coa_model.create_account(
            code="1010",
            name="API Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
        )

        root_qs = coa_model.get_coa_root_accounts_qs()
        non_root_qs = coa_model.get_non_root_coa_accounts_qs()

        self.assertTrue(root_qs.exists())
        self.assertFalse(root_qs.filter(uuid=cash_account.uuid).exists())
        self.assertTrue(non_root_qs.filter(uuid=cash_account.uuid).exists())

        for root_account in root_qs:
            self.assertFalse(non_root_qs.filter(uuid=root_account.uuid).exists())

    def test_get_coa_accounts_active_only_controls_active_filter_for_non_root_accounts(self):
        _entity_model, coa_model = self.create_coa(name="API CoA Account Active Filter")
        active_account = coa_model.create_account(
            code="1010",
            name="API Active Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
        )
        inactive_account = coa_model.create_account(
            code="6010",
            name="API Inactive Expense Account",
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=False,
        )

        active_qs = coa_model.get_coa_accounts(active_only=True)
        all_non_root_qs = coa_model.get_coa_accounts(active_only=False)

        self.assertTrue(active_qs.filter(uuid=active_account.uuid).exists())
        self.assertFalse(active_qs.filter(uuid=inactive_account.uuid).exists())

        self.assertTrue(all_non_root_qs.filter(uuid=active_account.uuid).exists())
        self.assertTrue(all_non_root_qs.filter(uuid=inactive_account.uuid).exists())
        self.assertFalse(all_non_root_qs.filter(role__in=self.EXPECTED_ROOT_ROLES).exists())
