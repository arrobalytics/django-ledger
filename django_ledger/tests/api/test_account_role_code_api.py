"""
High-level API behavior tests for AccountModel role and code helpers.

These tests cover validation, representative role mappings, account-code
generation/cleaning, and role-default contracts.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    COGS,
    CREDIT,
    DEBIT,
    EQUITY_CAPITAL,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
    ROOT_ASSETS,
    ROOT_CAPITAL,
    ROOT_COA,
    ROOT_EXPENSES,
    ROOT_GROUP,
    ROOT_INCOME,
    ROOT_LIABILITIES,
)
from django_ledger.models import AccountModel
from django_ledger.models.accounts import (
    AccountModelValidationError,
    account_code_validator,
)
from django_ledger.models.chart_of_accounts import ChartOfAccountsModelValidationError
from django_ledger.models.entity import EntityModel
from django_ledger.settings import (
    DJANGO_LEDGER_ACCOUNT_CODE_GENERATE,
    DJANGO_LEDGER_ACCOUNT_CODE_USE_PREFIX,
)


class AccountRoleCodeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_account_role_code_user",
            email="api-account-role-code-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Account Role Code Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_entity_with_default_coa(self, *, name="API Account Role Code Entity"):
        entity_model = self.create_entity(name=name)
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        entity_model.refresh_from_db()
        return entity_model, coa_model

    def make_account(
        self,
        *,
        role=ASSET_CA_CASH,
        balance_type=DEBIT,
        code="1010",
        name="API Role Code Account",
    ):
        return AccountModel(
            code=code,
            name=name,
            role=role,
            balance_type=balance_type,
            active=True,
        )

    def test_account_code_validator_accepts_alphanumeric_codes(self):
        for code in ("1010", "ABC123", "cash001"):
            with self.subTest(code=code):
                account_code_validator(code)

    def test_account_code_validator_rejects_non_alphanumeric_codes(self):
        for code in ("10-10", "cash_001", "cash 001"):
            with self.subTest(code=code):
                with self.assertRaises(AccountModelValidationError):
                    account_code_validator(code)

    def test_get_code_prefix_returns_representative_role_prefixes(self):
        role_cases = (
            (ASSET_CA_CASH, DEBIT, "1"),
            (LIABILITY_CL_ACC_PAYABLE, CREDIT, "2"),
            (EQUITY_CAPITAL, CREDIT, "3"),
            (INCOME_OPERATIONAL, CREDIT, "4"),
            (COGS, DEBIT, "5"),
            (EXPENSE_OPERATIONAL, DEBIT, "6"),
        )

        for role, balance_type, expected_prefix in role_cases:
            with self.subTest(role=role):
                account_model = self.make_account(
                    role=role,
                    balance_type=balance_type,
                    code=f"{expected_prefix}010",
                )

                self.assertEqual(account_model.get_code_prefix(), expected_prefix)

    def test_get_root_role_returns_representative_role_mappings(self):
        role_cases = (
            (ASSET_CA_CASH, DEBIT, ROOT_ASSETS),
            (LIABILITY_CL_ACC_PAYABLE, CREDIT, ROOT_LIABILITIES),
            (EQUITY_CAPITAL, CREDIT, ROOT_CAPITAL),
            (INCOME_OPERATIONAL, CREDIT, ROOT_INCOME),
            (EXPENSE_OPERATIONAL, DEBIT, ROOT_EXPENSES),
            (ROOT_COA, DEBIT, ROOT_COA),
        )

        for role, balance_type, expected_root_role in role_cases:
            with self.subTest(role=role):
                account_model = self.make_account(
                    role=role,
                    balance_type=balance_type,
                )

                self.assertEqual(account_model.get_root_role(), expected_root_role)

    def test_get_root_role_currently_returns_root_group_for_cogs(self):
        account_model = self.make_account(
            role=COGS,
            balance_type=DEBIT,
            code="5010",
        )

        self.assertEqual(account_model.get_root_role(), ROOT_GROUP)

    def test_get_bs_bucket_returns_representative_buckets(self):
        role_cases = (
            (ASSET_CA_CASH, DEBIT, "Asset"),
            (LIABILITY_CL_ACC_PAYABLE, CREDIT, "Liability"),
            (EQUITY_CAPITAL, CREDIT, "Capital"),
            (INCOME_OPERATIONAL, CREDIT, "Income"),
            (COGS, DEBIT, "COGS"),
            (EXPENSE_OPERATIONAL, DEBIT, "Expenses"),
        )

        for role, balance_type, expected_bucket in role_cases:
            with self.subTest(role=role):
                account_model = self.make_account(
                    role=role,
                    balance_type=balance_type,
                )

                self.assertEqual(account_model.get_bs_bucket(), expected_bucket)

    def test_clean_validates_role_prefix_when_prefix_setting_is_enabled(self):
        if not DJANGO_LEDGER_ACCOUNT_CODE_USE_PREFIX:
            self.skipTest("Account code prefix validation is disabled by settings.")

        account_model = self.make_account(
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            code="2010",
        )

        with self.assertRaises(AccountModelValidationError):
            account_model.clean()

    def test_clean_generates_account_code_with_role_prefix_when_enabled(self):
        if not DJANGO_LEDGER_ACCOUNT_CODE_GENERATE:
            self.skipTest("Account code generation is disabled by settings.")

        account_model = self.make_account(
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            code="",
        )

        account_model.clean()

        self.assertRegex(account_model.code, r"^1[0-9]{5}$")
        self.assertTrue(account_model.code.isalnum())

    def test_role_default_false_is_normalized_to_none_on_save(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Role Default Normalize Entity",
        )

        account_model = coa_model.create_account(
            code="1010",
            name="API Non Default Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=False,
        )

        account_model.refresh_from_db()
        self.assertIsNone(account_model.role_default)

    def test_role_default_uniqueness_rejects_second_default_for_same_role(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Role Default Unique Entity",
        )

        first_default = coa_model.create_account(
            code="1010",
            name="API Default Cash Account",
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

        self.assertTrue(
            AccountModel.objects.filter(uuid=first_default.uuid, role_default=True).exists()
        )
        self.assertFalse(
            AccountModel.objects.filter(
                coa_model=coa_model,
                code="1020",
                role=ASSET_CA_CASH,
            ).exists()
        )
