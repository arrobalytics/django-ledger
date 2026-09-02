"""
High-level API behavior tests for AccountModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import AccountModel
from django_ledger.models.entity import EntityModel


class AccountHighLevelAPITest(TestCase):
    """
    High-level behavior tests for AccountModel public API contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document small, deterministic business invariants that should
    remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_account_contract_user",
            email="api-account-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Account Contract Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_entity_with_default_coa(self):
        entity_model = self.create_entity()
        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Account Contract CoA",
            commit=True,
            assign_as_default=True,
        )
        entity_model.refresh_from_db()
        return entity_model, coa_model

    def test_create_account_adds_non_root_transaction_account(self):
        entity_model, coa_model = self.create_entity_with_default_coa()

        account_model = coa_model.create_account(
            code="1010",
            name="API Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        account_model.refresh_from_db()

        self.assertEqual(account_model.coa_model_id, coa_model.uuid)
        self.assertFalse(account_model.is_root_account())
        self.assertTrue(account_model.active)
        self.assertFalse(account_model.locked)
        self.assertTrue(account_model.can_transact())

        self.assertTrue(
            AccountModel.objects.for_entity(entity_model)
            .not_coa_root()
            .filter(uuid=account_model.uuid)
            .exists()
        )

    def test_created_account_is_inserted_under_matching_role_root(self):
        entity_model, coa_model = self.create_entity_with_default_coa()

        account_model = coa_model.create_account(
            code="6010",
            name="API Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
        )

        account_model.refresh_from_db()

        ancestors = list(account_model.get_ancestors())

        self.assertGreater(
            len(ancestors),
            0,
            "A real account should be inserted under the configured CoA tree.",
        )

        self.assertTrue(
            any(ancestor.is_root_account() for ancestor in ancestors),
            "A real account should have a technical CoA root ancestor.",
        )

        self.assertEqual(account_model.role, "ex_regular")
        self.assertEqual(account_model.balance_type, "debit")
        self.assertEqual(account_model.coa_model_id, coa_model.uuid)

    def test_inactive_account_is_excluded_from_available_queryset(self):
        entity_model, coa_model = self.create_entity_with_default_coa()

        account_model = coa_model.create_account(
            code="1020",
            name="API Inactive Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=False,
        )

        account_model.refresh_from_db()

        self.assertFalse(account_model.active)
        self.assertFalse(
            AccountModel.objects.for_entity(entity_model)
            .available()
            .filter(uuid=account_model.uuid)
            .exists()
        )

    def test_locked_account_cannot_transact(self):
        _entity_model, coa_model = self.create_entity_with_default_coa()

        account_model = coa_model.create_account(
            code="1030",
            name="API Locked Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        account_model.locked = True
        account_model.save(update_fields=["locked"])
        account_model.refresh_from_db()

        self.assertTrue(account_model.active)
        self.assertTrue(account_model.locked)
        self.assertFalse(account_model.can_transact())

    def test_available_queryset_excludes_inactive_and_locked_accounts(self):
        entity_model, coa_model = self.create_entity_with_default_coa()

        available_account = coa_model.create_account(
            code="1040",
            name="API Available Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        inactive_account = coa_model.create_account(
            code="1050",
            name="API Inactive Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=False,
        )

        locked_account = coa_model.create_account(
            code="1060",
            name="API Locked Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )
        locked_account.locked = True
        locked_account.save(update_fields=["locked"])

        available_qs = AccountModel.objects.for_entity(entity_model).available()

        self.assertTrue(available_qs.filter(uuid=available_account.uuid).exists())
        self.assertFalse(available_qs.filter(uuid=inactive_account.uuid).exists())
        self.assertFalse(available_qs.filter(uuid=locked_account.uuid).exists())

    def test_not_coa_root_excludes_technical_root_accounts(self):
        entity_model, coa_model = self.create_entity_with_default_coa()

        real_account = coa_model.create_account(
            code="1070",
            name="API Real Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        all_accounts_qs = AccountModel.objects.for_entity(entity_model)
        root_accounts_qs = all_accounts_qs.is_coa_root()
        real_accounts_qs = all_accounts_qs.not_coa_root()

        self.assertGreater(root_accounts_qs.count(), 0)
        self.assertTrue(real_accounts_qs.filter(uuid=real_account.uuid).exists())

        for root_account in root_accounts_qs:
            self.assertFalse(
                real_accounts_qs.filter(uuid=root_account.uuid).exists(),
                "Technical CoA root accounts should be excluded by not_coa_root().",
            )

    def test_role_default_account_is_exposed_by_queryset_helper(self):
        entity_model, coa_model = self.create_entity_with_default_coa()

        default_cash_account = coa_model.create_account(
            code="1080",
            name="API Default Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        non_default_cash_account = coa_model.create_account(
            code="1090",
            name="API Non Default Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        role_default_qs = AccountModel.objects.for_entity(entity_model).is_role_default()

        self.assertTrue(role_default_qs.filter(uuid=default_cash_account.uuid).exists())
        self.assertFalse(role_default_qs.filter(uuid=non_default_cash_account.uuid).exists())

    def test_role_specific_queryset_helpers_expose_expected_accounts(self):
        entity_model, coa_model = self.create_entity_with_default_coa()

        cash_account = coa_model.create_account(
            code="1100",
            name="API Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        expense_account = coa_model.create_account(
            code="6110",
            name="API Regular Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
        )

        accounts_qs = AccountModel.objects.for_entity(entity_model).not_coa_root()

        self.assertTrue(accounts_qs.cash().filter(uuid=cash_account.uuid).exists())
        self.assertFalse(accounts_qs.cash().filter(uuid=expense_account.uuid).exists())

        self.assertTrue(accounts_qs.expenses().filter(uuid=expense_account.uuid).exists())
        self.assertFalse(accounts_qs.expenses().filter(uuid=cash_account.uuid).exists())
