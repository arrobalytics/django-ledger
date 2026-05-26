"""
High-level API behavior tests for EntityModel and ChartOfAccountModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import AccountModel
from django_ledger.models.entity import EntityModel


class EntityChartOfAccountsHighLevelAPITest(TestCase):
    """
    High-level behavior tests for the public Entity -> CoA -> Account setup API.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document small, deterministic business contracts that should
    remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_contract_user",
            email="api-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Contract Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def test_create_entity_produces_usable_accounting_entity(self):
        entity_model = self.create_entity()

        self.assertIsNotNone(entity_model.uuid)
        self.assertEqual(entity_model.name, "API Contract Entity")
        self.assertEqual(entity_model.admin, self.user)
        self.assertTrue(entity_model.accrual_method)
        self.assertEqual(entity_model.fy_start_month, 1)

    def test_create_chart_of_accounts_can_assign_default_coa(self):
        entity_model = self.create_entity()

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        entity_model.refresh_from_db()

        self.assertIsNotNone(coa_model.uuid)
        self.assertEqual(coa_model.name, "API Contract CoA")
        self.assertEqual(coa_model.entity_id, entity_model.uuid)
        self.assertTrue(coa_model.active)
        self.assertEqual(entity_model.default_coa_id, coa_model.uuid)

    def test_create_chart_of_accounts_configures_root_account_tree(self):
        entity_model = self.create_entity()

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        self.assertTrue(
            coa_model.is_configured(),
            "A CoA created through the high-level API should be configured.",
        )

        accounts_qs = AccountModel.objects.for_entity(entity_model)
        root_accounts_qs = accounts_qs.is_coa_root()

        self.assertGreater(
            root_accounts_qs.count(),
            0,
            "A configured CoA should include technical root accounts.",
        )

        for root_account in root_accounts_qs:
            self.assertTrue(root_account.locked)
            self.assertFalse(root_account.active)
            self.assertTrue(root_account.role_default)

    def test_create_account_adds_real_account_to_default_coa(self):
        entity_model = self.create_entity()

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        account_model = coa_model.create_account(
            code="1010",
            name="API Contract Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        account_model.refresh_from_db()

        self.assertEqual(account_model.coa_model_id, coa_model.uuid)
        self.assertEqual(account_model.code, "1010")
        self.assertEqual(account_model.name, "API Contract Cash Account")
        self.assertEqual(account_model.role, "asset_ca_cash")
        self.assertEqual(account_model.balance_type, "debit")
        self.assertTrue(account_model.active)
        self.assertFalse(account_model.locked)
        self.assertFalse(account_model.is_root_account())
        self.assertTrue(account_model.can_transact())

    def test_default_entity_account_queryset_exposes_created_real_account(self):
        entity_model = self.create_entity()

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        account_model = coa_model.create_account(
            code="1020",
            name="API Contract Bank Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        default_coa_accounts = AccountModel.objects.for_entity(entity_model)

        self.assertTrue(
            default_coa_accounts.filter(uuid=account_model.uuid).exists(),
            "AccountModel.objects.for_entity(entity) should expose accounts "
            "from the entity default CoA.",
        )

        self.assertTrue(
            default_coa_accounts.not_coa_root().filter(uuid=account_model.uuid).exists(),
            "A real account created via the CoA API should not be treated as "
            "a technical CoA root account.",
        )
