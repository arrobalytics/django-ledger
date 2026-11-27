"""
High-level API behavior tests for AccountModel move-choice and display helpers.

These tests cover representative tree/display helper behavior without URL,
lifecycle, filter, or role-code assertions.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_PPE_BUILDINGS,
    ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION,
    CREDIT,
    DEBIT,
    ROOT_ASSETS,
)
from django_ledger.models import AccountModel
from django_ledger.models.entity import EntityModel


class AccountMoveDisplayAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_account_move_display_user",
            email="api-account-move-display-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Account Move Display Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_entity_with_default_coa(self, *, name="API Account Move Display Entity"):
        entity_model = self.create_entity(name=name)
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        entity_model.refresh_from_db()
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
    ):
        return coa_model.create_account(
            code=code,
            name=name,
            role=role,
            balance_type=balance_type,
            active=active,
        )

    def test_get_account_move_choice_queryset_returns_legal_same_coa_candidates(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Move Choice Entity",
        )
        _other_entity, other_coa = self.create_entity_with_default_coa(
            name="API Account Other Move Choice Entity",
        )
        same_role_candidate = self.create_account(
            coa_model,
            code="1790",
            name="API Building Accumulated Depreciation Candidate",
            role=ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION,
            balance_type=CREDIT,
        )
        valid_parent_candidate = self.create_account(
            coa_model,
            code="1710",
            name="API Building Parent Candidate",
            role=ASSET_PPE_BUILDINGS,
            balance_type=DEBIT,
        )
        account_model = self.create_account(
            coa_model,
            code="1795",
            name="API Building Accumulated Depreciation Account",
            role=ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION,
            balance_type=CREDIT,
        )
        other_coa_candidate = self.create_account(
            other_coa,
            code="1790",
            name="API Other CoA Building Candidate",
            role=ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION,
            balance_type=CREDIT,
        )
        root_asset_account = AccountModel.objects.for_entity(coa_model.entity).get(
            role=ROOT_ASSETS,
        )

        choice_qs = account_model.get_account_move_choice_queryset()

        self.assertTrue(choice_qs.filter(uuid=same_role_candidate.uuid).exists())
        self.assertTrue(choice_qs.filter(uuid=valid_parent_candidate.uuid).exists())
        self.assertTrue(choice_qs.filter(uuid=root_asset_account.uuid).exists())
        self.assertFalse(choice_qs.filter(uuid=account_model.uuid).exists())
        self.assertFalse(choice_qs.filter(uuid=other_coa_candidate.uuid).exists())

    def test_indentation_helpers_reflect_current_tree_depth(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Indent Entity",
        )
        root_asset_account = AccountModel.objects.for_entity(coa_model.entity).get(
            role=ROOT_ASSETS,
        )
        cash_account = self.create_account(
            coa_model,
            code="1010",
            name="API Cash Indent Account",
        )

        self.assertFalse(root_asset_account.is_indented())
        self.assertEqual(root_asset_account.get_html_pixel_indent(), "0px")

        self.assertTrue(cash_account.is_indented())
        self.assertEqual(
            cash_account.get_html_pixel_indent(),
            f"{(cash_account.depth - 2) * 40}px",
        )

    def test_string_helpers_include_stable_account_fragments(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account String Entity",
        )
        account_model = self.create_account(
            coa_model,
            code="1010",
            name="API Cash Display Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
        )

        string_value = str(account_model)
        alt_string_value = account_model.alt_str()

        for fragment in (
            "1010",
            "API Cash Display Account",
            ASSET_CA_CASH.upper(),
            DEBIT,
            account_model.role_bs.upper(),
        ):
            with self.subTest(fragment=fragment, display="__str__"):
                self.assertIn(fragment, string_value)

        for fragment in (
            "1010",
            "API Cash Display Account",
            ASSET_CA_CASH.upper(),
            DEBIT,
        ):
            with self.subTest(fragment=fragment, display="alt_str"):
                self.assertIn(fragment, alt_string_value)
