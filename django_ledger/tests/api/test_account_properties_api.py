"""
High-level API behavior tests for AccountModel properties and instance helpers.

These tests cover model-level helper behavior without queryset filter or
lifecycle transition assertions.
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
    ROOT_COA,
)
from django_ledger.models import AccountModel
from django_ledger.models.entity import EntityModel


class AccountPropertiesAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_account_properties_user",
            email="api-account-properties-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Account Properties Entity"):
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
        name="API Account Properties CoA",
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

    def create_entity_with_default_coa(self, *, name="API Account Properties Entity"):
        entity_model = self.create_entity(name=name)
        coa_model = self.create_coa(entity_model, name=f"{name} CoA")
        return entity_model, coa_model

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
    ):
        account_model = coa_model.create_account(
            code=code,
            name=name,
            role=role,
            balance_type=balance_type,
            active=active,
        )
        if locked:
            account_model.locked = True
            account_model.save(update_fields=["locked", "updated"])
        return account_model

    def make_direct_account(self, coa_model):
        return AccountModel(
            code="1999",
            name="API Direct Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            coa_model=coa_model,
        )

    def test_coa_slug_uses_manager_annotation_and_direct_instance_fallback(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account CoA Slug Entity",
        )
        account_model = self.create_account(
            coa_model,
            code="1010",
            name="API Account CoA Slug",
        )

        annotated_account = AccountModel.objects.get(uuid=account_model.uuid)
        direct_account = self.make_direct_account(coa_model)

        self.assertEqual(annotated_account.coa_slug, coa_model.slug)
        self.assertEqual(direct_account.coa_slug, coa_model.slug)

    def test_entity_slug_uses_manager_annotation_and_currently_has_no_direct_fallback(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Entity Slug Entity",
        )
        account_model = self.create_account(
            coa_model,
            code="1010",
            name="API Account Entity Slug",
        )

        annotated_account = AccountModel.objects.get(uuid=account_model.uuid)
        direct_account = self.make_direct_account(coa_model)

        self.assertEqual(annotated_account.entity_slug, entity_model.slug)
        with self.assertRaises(AttributeError):
            direct_account.entity_slug

    def test_role_balance_and_root_helpers_reflect_account_role(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Role Balance Entity",
        )
        cash_account = self.create_account(
            coa_model,
            code="1010",
            name="API Debit Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
        )
        payable_account = self.create_account(
            coa_model,
            code="2010",
            name="API Credit Payable Account",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type=CREDIT,
        )
        coa_root_account = AccountModel.objects.for_entity(coa_model.entity).get(
            role=ROOT_COA,
        )

        self.assertEqual(cash_account.role_bs, "assets")
        self.assertFalse(cash_account.is_root_account())
        self.assertFalse(cash_account.is_coa_root())
        self.assertTrue(cash_account.is_debit())
        self.assertFalse(cash_account.is_credit())

        self.assertTrue(payable_account.is_credit())
        self.assertFalse(payable_account.is_debit())

        self.assertTrue(coa_root_account.is_root_account())
        self.assertTrue(coa_root_account.is_coa_root())

    def test_role_category_helpers_identify_representative_roles(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Role Category Entity",
        )
        asset_account = self.create_account(
            coa_model,
            code="1010",
            name="API Asset Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
        )
        liability_account = self.create_account(
            coa_model,
            code="2010",
            name="API Liability Account",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type=CREDIT,
        )
        capital_account = self.create_account(
            coa_model,
            code="3010",
            name="API Capital Account",
            role=EQUITY_CAPITAL,
            balance_type=CREDIT,
        )
        income_account = self.create_account(
            coa_model,
            code="4010",
            name="API Income Account",
            role=INCOME_OPERATIONAL,
            balance_type=CREDIT,
        )
        cogs_account = self.create_account(
            coa_model,
            code="5010",
            name="API COGS Account",
            role=COGS,
            balance_type=DEBIT,
        )
        expense_account = self.create_account(
            coa_model,
            code="6010",
            name="API Expense Account",
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
        )

        self.assertTrue(asset_account.is_asset())
        self.assertFalse(asset_account.is_liability())

        self.assertTrue(liability_account.is_liability())
        self.assertFalse(liability_account.is_asset())

        self.assertTrue(capital_account.is_capital())
        self.assertFalse(capital_account.is_income())

        self.assertTrue(income_account.is_income())
        self.assertFalse(income_account.is_capital())

        self.assertTrue(cogs_account.is_cogs())
        self.assertFalse(cogs_account.is_expense())

        self.assertTrue(expense_account.is_expense())
        self.assertFalse(expense_account.is_cogs())

    def test_state_helpers_reflect_account_and_coa_state(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account State Helper Entity",
        )
        active_account = self.create_account(
            coa_model,
            code="1010",
            name="API Active Account",
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
            name="API Inactive CoA",
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

        annotated_account = AccountModel.objects.get(uuid=active_account.uuid)
        direct_account = self.make_direct_account(coa_model)

        self.assertTrue(active_account.is_active())
        self.assertFalse(inactive_account.is_active())
        self.assertTrue(locked_account.is_locked())
        self.assertFalse(active_account.is_locked())

        self.assertTrue(annotated_account.is_coa_active())
        self.assertTrue(direct_account.is_coa_active())
        self.assertFalse(inactive_coa_account.is_coa_active())

    def test_model_can_transact_reflects_coa_and_lock_state(self):
        entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Can Transact Entity",
        )
        available_account = self.create_account(
            coa_model,
            code="1010",
            name="API Available Account",
            active=True,
            locked=False,
        )
        locked_account = self.create_account(
            coa_model,
            code="1020",
            name="API Locked Account",
            active=True,
            locked=True,
        )
        inactive_coa = self.create_coa(
            entity_model,
            name="API Can Transact Inactive CoA",
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

        self.assertTrue(available_account.can_transact())
        self.assertFalse(locked_account.can_transact())
        self.assertFalse(inactive_coa_account.can_transact())

    def test_model_can_transact_currently_does_not_depend_on_account_active_state(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Can Transact Inactive Account Entity",
        )
        inactive_account = self.create_account(
            coa_model,
            code="1010",
            name="API Inactive Account",
            active=False,
            locked=False,
        )

        self.assertFalse(inactive_account.is_active())
        self.assertTrue(inactive_account.can_transact())
