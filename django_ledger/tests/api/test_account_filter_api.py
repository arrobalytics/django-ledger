"""
High-level API behavior tests for AccountModel queryset filters.

These tests cover public account filtering helpers without lifecycle or model
property assertions.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.exceptions import InvalidRoleError
from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_PREPAID,
    ASSET_CA_RECEIVABLES,
    CREDIT,
    DEBIT,
    EXPENSE_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
    LIABILITY_CL_DEFERRED_REVENUE,
)
from django_ledger.models import AccountModel
from django_ledger.models.entity import EntityModel


class AccountFilterAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_account_filter_user",
            email="api-account-filter-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Account Filter Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_coa(
        self,
        entity_model,
        *,
        name="API Account Filter CoA",
        active=True,
        assign_as_default=True,
    ):
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=name,
            commit=True,
            assign_as_default=assign_as_default,
        )
        if coa_model.active != active:
            coa_model.active = active
            coa_model.save(update_fields=["active", "updated"])
        entity_model.refresh_from_db()
        return coa_model

    def create_account(
        self,
        coa_model,
        *,
        code,
        name,
        role=ASSET_CA_CASH,
        balance_type=DEBIT,
        active=True,
        locked=False,
        is_role_default=False,
    ):
        account_model = coa_model.create_account(
            code=code,
            name=name,
            role=role,
            balance_type=balance_type,
            active=active,
            is_role_default=is_role_default,
        )
        if locked:
            account_model.locked = True
            account_model.save(update_fields=["locked", "updated"])
        return account_model

    def create_entity_with_default_coa(self, *, name="API Account Filter Entity"):
        entity_model = self.create_entity(name=name)
        coa_model = self.create_coa(entity_model, name=f"{name} CoA")
        return entity_model, coa_model

    def test_active_inactive_locked_and_unlocked_filters_return_matching_accounts(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account State Filter Entity",
        )
        active_account = self.create_account(
            coa_model,
            code="1010",
            name="API Active Account",
            active=True,
        )
        inactive_account = self.create_account(
            coa_model,
            code="1020",
            name="API Inactive Account",
            active=False,
        )
        locked_account = self.create_account(
            coa_model,
            code="1030",
            name="API Locked Account",
            active=True,
            locked=True,
        )

        account_qs = AccountModel.objects.for_entity(entity_model).not_coa_root()

        self.assertTrue(account_qs.active().filter(uuid=active_account.uuid).exists())
        self.assertFalse(account_qs.active().filter(uuid=inactive_account.uuid).exists())

        self.assertTrue(account_qs.inactive().filter(uuid=inactive_account.uuid).exists())
        self.assertFalse(account_qs.inactive().filter(uuid=active_account.uuid).exists())

        self.assertTrue(account_qs.locked().filter(uuid=locked_account.uuid).exists())
        self.assertFalse(account_qs.locked().filter(uuid=active_account.uuid).exists())

        self.assertTrue(account_qs.unlocked().filter(uuid=active_account.uuid).exists())
        self.assertFalse(account_qs.unlocked().filter(uuid=locked_account.uuid).exists())

    def test_with_roles_accepts_single_role_and_role_list(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Role Filter Entity",
        )
        cash_account = self.create_account(
            coa_model,
            code="1010",
            name="API Cash Account",
            role=ASSET_CA_CASH,
        )
        expense_account = self.create_account(
            coa_model,
            code="6010",
            name="API Expense Account",
            role=EXPENSE_OPERATIONAL,
        )
        payable_account = self.create_account(
            coa_model,
            code="2010",
            name="API Payable Account",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type=CREDIT,
        )

        account_qs = AccountModel.objects.for_entity(entity_model).not_coa_root()

        cash_qs = account_qs.with_roles(ASSET_CA_CASH)
        self.assertTrue(cash_qs.filter(uuid=cash_account.uuid).exists())
        self.assertFalse(cash_qs.filter(uuid=expense_account.uuid).exists())

        cash_and_expense_qs = account_qs.with_roles([
            ASSET_CA_CASH,
            EXPENSE_OPERATIONAL,
        ])
        self.assertTrue(cash_and_expense_qs.filter(uuid=cash_account.uuid).exists())
        self.assertTrue(cash_and_expense_qs.filter(uuid=expense_account.uuid).exists())
        self.assertFalse(cash_and_expense_qs.filter(uuid=payable_account.uuid).exists())

    def test_with_roles_rejects_invalid_role(self):
        entity_model, _coa_model = self.create_entity_with_default_coa(
            name="API Account Invalid Role Filter Entity",
        )

        with self.assertRaises(InvalidRoleError):
            AccountModel.objects.for_entity(entity_model).with_roles("not_a_real_role")

    def test_with_codes_accepts_string_list_and_set(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Code Filter Entity",
        )
        first_account = self.create_account(
            coa_model,
            code="1010",
            name="API First Code Account",
        )
        second_account = self.create_account(
            coa_model,
            code="1020",
            name="API Second Code Account",
        )
        third_account = self.create_account(
            coa_model,
            code="1030",
            name="API Third Code Account",
        )

        account_qs = AccountModel.objects.for_entity(entity_model).not_coa_root()

        single_code_qs = account_qs.with_codes("1010")
        self.assertTrue(single_code_qs.filter(uuid=first_account.uuid).exists())
        self.assertFalse(single_code_qs.filter(uuid=second_account.uuid).exists())

        for codes in (["1010", "1020"], {"1010", "1020"}):
            with self.subTest(codes=codes):
                code_qs = account_qs.with_codes(codes)

                self.assertTrue(code_qs.filter(uuid=first_account.uuid).exists())
                self.assertTrue(code_qs.filter(uuid=second_account.uuid).exists())
                self.assertFalse(code_qs.filter(uuid=third_account.uuid).exists())

    def test_cash_and_expenses_filters_return_matching_roles(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Cash Expense Filter Entity",
        )
        cash_account = self.create_account(
            coa_model,
            code="1010",
            name="API Cash Account",
            role=ASSET_CA_CASH,
        )
        expense_account = self.create_account(
            coa_model,
            code="6010",
            name="API Expense Account",
            role=EXPENSE_OPERATIONAL,
        )

        account_qs = AccountModel.objects.for_entity(entity_model).not_coa_root()

        self.assertTrue(account_qs.cash().filter(uuid=cash_account.uuid).exists())
        self.assertFalse(account_qs.cash().filter(uuid=expense_account.uuid).exists())

        self.assertTrue(account_qs.expenses().filter(uuid=expense_account.uuid).exists())
        self.assertFalse(account_qs.expenses().filter(uuid=cash_account.uuid).exists())

    def test_root_and_role_default_filters_expose_expected_accounts(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Root Default Filter Entity",
        )
        default_cash_account = self.create_account(
            coa_model,
            code="1010",
            name="API Default Cash Account",
            role=ASSET_CA_CASH,
            is_role_default=True,
        )
        non_default_cash_account = self.create_account(
            coa_model,
            code="1020",
            name="API Non Default Cash Account",
            role=ASSET_CA_CASH,
        )

        account_qs = AccountModel.objects.for_entity(entity_model)
        root_qs = account_qs.is_coa_root()
        real_account_qs = account_qs.not_coa_root()
        role_default_qs = account_qs.is_role_default()

        self.assertGreater(root_qs.count(), 0)
        self.assertTrue(real_account_qs.filter(uuid=default_cash_account.uuid).exists())

        for root_account in root_qs:
            self.assertFalse(real_account_qs.filter(uuid=root_account.uuid).exists())

        self.assertTrue(role_default_qs.filter(uuid=default_cash_account.uuid).exists())
        self.assertFalse(role_default_qs.filter(uuid=non_default_cash_account.uuid).exists())

    def test_can_transact_and_available_filters_exclude_unavailable_accounts(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Available Filter Entity",
        )
        available_account = self.create_account(
            coa_model,
            code="1010",
            name="API Available Account",
            active=True,
            locked=False,
        )
        inactive_account = self.create_account(
            coa_model,
            code="1020",
            name="API Inactive Account",
            active=False,
            locked=False,
        )
        locked_account = self.create_account(
            coa_model,
            code="1030",
            name="API Locked Account",
            active=True,
            locked=True,
        )
        inactive_coa = self.create_coa(
            entity_model,
            name="API Account Inactive CoA",
            active=False,
            assign_as_default=False,
        )
        inactive_coa_account = self.create_account(
            inactive_coa,
            code="1010",
            name="API Inactive CoA Account",
            active=True,
            locked=False,
        )

        default_account_qs = AccountModel.objects.for_entity(entity_model).not_coa_root()
        inactive_coa_qs = AccountModel.objects.for_entity(
            entity_model,
            coa_model=inactive_coa,
        ).not_coa_root()

        for filter_name in ("can_transact", "available"):
            with self.subTest(filter_name=filter_name):
                default_filtered_qs = getattr(default_account_qs, filter_name)()
                inactive_coa_filtered_qs = getattr(inactive_coa_qs, filter_name)()

                self.assertTrue(default_filtered_qs.filter(uuid=available_account.uuid).exists())
                self.assertFalse(default_filtered_qs.filter(uuid=inactive_account.uuid).exists())
                self.assertFalse(default_filtered_qs.filter(uuid=locked_account.uuid).exists())
                self.assertFalse(
                    inactive_coa_filtered_qs.filter(uuid=inactive_coa_account.uuid).exists()
                )

    def test_for_bill_returns_available_bill_role_accounts_only(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Bill Filter Entity",
        )
        cash_account = self.create_account(
            coa_model,
            code="1010",
            name="API Bill Cash Account",
            role=ASSET_CA_CASH,
        )
        prepaid_account = self.create_account(
            coa_model,
            code="1210",
            name="API Bill Prepaid Account",
            role=ASSET_CA_PREPAID,
        )
        payable_account = self.create_account(
            coa_model,
            code="2010",
            name="API Bill Payable Account",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type=CREDIT,
        )
        receivable_account = self.create_account(
            coa_model,
            code="1310",
            name="API Invoice Receivable Account",
            role=ASSET_CA_RECEIVABLES,
        )
        deferred_revenue_account = self.create_account(
            coa_model,
            code="2210",
            name="API Invoice Deferred Revenue Account",
            role=LIABILITY_CL_DEFERRED_REVENUE,
            balance_type=CREDIT,
        )
        expense_account = self.create_account(
            coa_model,
            code="6010",
            name="API Expense Account",
            role=EXPENSE_OPERATIONAL,
        )

        bill_qs = AccountModel.objects.for_entity(entity_model).for_bill()

        self.assertTrue(bill_qs.filter(uuid=cash_account.uuid).exists())
        self.assertTrue(bill_qs.filter(uuid=prepaid_account.uuid).exists())
        self.assertTrue(bill_qs.filter(uuid=payable_account.uuid).exists())
        self.assertFalse(bill_qs.filter(uuid=receivable_account.uuid).exists())
        self.assertFalse(bill_qs.filter(uuid=deferred_revenue_account.uuid).exists())
        self.assertFalse(bill_qs.filter(uuid=expense_account.uuid).exists())

    def test_for_invoice_returns_available_invoice_role_accounts_only(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Invoice Filter Entity",
        )
        cash_account = self.create_account(
            coa_model,
            code="1010",
            name="API Invoice Cash Account",
            role=ASSET_CA_CASH,
        )
        receivable_account = self.create_account(
            coa_model,
            code="1210",
            name="API Invoice Receivable Account",
            role=ASSET_CA_RECEIVABLES,
        )
        deferred_revenue_account = self.create_account(
            coa_model,
            code="2010",
            name="API Invoice Deferred Revenue Account",
            role=LIABILITY_CL_DEFERRED_REVENUE,
            balance_type=CREDIT,
        )
        prepaid_account = self.create_account(
            coa_model,
            code="1310",
            name="API Bill Prepaid Account",
            role=ASSET_CA_PREPAID,
        )
        payable_account = self.create_account(
            coa_model,
            code="2210",
            name="API Bill Payable Account",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type=CREDIT,
        )
        expense_account = self.create_account(
            coa_model,
            code="6010",
            name="API Expense Account",
            role=EXPENSE_OPERATIONAL,
        )

        invoice_qs = AccountModel.objects.for_entity(entity_model).for_invoice()

        self.assertTrue(invoice_qs.filter(uuid=cash_account.uuid).exists())
        self.assertTrue(invoice_qs.filter(uuid=receivable_account.uuid).exists())
        self.assertTrue(invoice_qs.filter(uuid=deferred_revenue_account.uuid).exists())
        self.assertFalse(invoice_qs.filter(uuid=prepaid_account.uuid).exists())
        self.assertFalse(invoice_qs.filter(uuid=payable_account.uuid).exists())
        self.assertFalse(invoice_qs.filter(uuid=expense_account.uuid).exists())
