"""
High-level API behavior tests for BankAccountModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import BankAccountModel
from django_ledger.models.bank_account import BankAccountValidationError
from django_ledger.models.entity import EntityModel


class BankAccountHighLevelAPITest(TestCase):
    """
    High-level behavior tests for BankAccountModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic bank-account invariants that should
    remain true across swappable-model refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_bank_account_contract_user",
            email="api-bank-account-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Bank Account Contract Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )

        cash_account = coa_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "expense_account": expense_account,
        }

    def create_bank_account(
        self,
        setup,
        *,
        name="API Bank Account",
        account_number="000123456789",
        routing_number="000111000",
        active=False,
        hidden=False,
    ):
        bank_account = BankAccountModel(
            name=name,
            account_model=setup["cash_account"],
            account_number=account_number,
            routing_number=routing_number,
            active=active,
            hidden=hidden,
        )

        bank_account.configure(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )

        bank_account.refresh_from_db()
        return bank_account

    def test_bank_account_configure_binds_entity_and_account(self):
        setup = self.create_entity_setup()

        bank_account = self.create_bank_account(setup)

        self.assertIsInstance(bank_account, BankAccountModel)
        self.assertIsNotNone(bank_account.uuid)
        self.assertEqual(bank_account.entity_model_id, setup["entity_model"].uuid)
        self.assertEqual(bank_account.account_model_id, setup["cash_account"].uuid)
        self.assertEqual(bank_account.name, "API Bank Account")
        self.assertEqual(bank_account.account_number, "000123456789")
        self.assertEqual(bank_account.routing_number, "000111000")

    def test_bank_account_for_entity_limits_queryset_to_entity_scope(self):
        setup = self.create_entity_setup(name="API Bank Account Entity A")
        other_setup = self.create_entity_setup(name="API Bank Account Entity B")

        bank_account = self.create_bank_account(
            setup,
            account_number="000123456789",
            routing_number="000111000",
        )

        other_bank_account = self.create_bank_account(
            other_setup,
            account_number="000123456789",
            routing_number="000111000",
        )

        scoped_qs = BankAccountModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(scoped_qs.filter(uuid=bank_account.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_bank_account.uuid).exists())

    def test_bank_account_active_queryset_and_state_transitions(self):
        setup = self.create_entity_setup()

        bank_account = self.create_bank_account(setup, active=False)

        bank_accounts_qs = BankAccountModel.objects.for_entity(setup["entity_model"])

        self.assertFalse(bank_account.is_active())
        self.assertTrue(bank_account.can_activate())
        self.assertFalse(bank_accounts_qs.active().filter(uuid=bank_account.uuid).exists())

        bank_account.mark_as_active(commit=True)
        bank_account.refresh_from_db()

        self.assertTrue(bank_account.is_active())
        self.assertTrue(bank_account.can_inactivate())
        self.assertTrue(bank_accounts_qs.active().filter(uuid=bank_account.uuid).exists())

        bank_account.mark_as_inactive(commit=True)
        bank_account.refresh_from_db()

        self.assertFalse(bank_account.is_active())
        self.assertTrue(bank_account.can_activate())
        self.assertFalse(bank_accounts_qs.active().filter(uuid=bank_account.uuid).exists())

    def test_bank_account_hidden_queryset_and_state_helpers(self):
        setup = self.create_entity_setup()

        visible_bank_account = self.create_bank_account(
            setup,
            account_number="000123456789",
            routing_number="000111000",
            hidden=False,
        )

        hidden_bank_account = self.create_bank_account(
            setup,
            account_number="000987654321",
            routing_number="000222000",
            hidden=True,
        )

        bank_accounts_qs = BankAccountModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(visible_bank_account.can_hide())
        self.assertFalse(visible_bank_account.can_unhide())

        self.assertFalse(hidden_bank_account.can_hide())
        self.assertTrue(hidden_bank_account.can_unhide())

        self.assertFalse(bank_accounts_qs.hidden().filter(uuid=visible_bank_account.uuid).exists())
        self.assertTrue(bank_accounts_qs.hidden().filter(uuid=hidden_bank_account.uuid).exists())

    def test_bank_account_rejects_invalid_entity_configure_input(self):
        setup = self.create_entity_setup()

        bank_account = BankAccountModel(
            name="API Invalid Bank Account",
            account_model=setup["cash_account"],
            account_number="000123456789",
            routing_number="000111000",
        )

        with self.assertRaises(BankAccountValidationError):
            bank_account.configure(
                entity_slug=None,
                user_model=self.user,
                commit=True,
            )

    def test_bank_account_requires_user_model_when_configuring_with_slug(self):
        setup = self.create_entity_setup()

        bank_account = BankAccountModel(
            name="API Slug Bank Account",
            account_model=setup["cash_account"],
            account_number="000123456789",
            routing_number="000111000",
        )

        with self.assertRaises(BankAccountValidationError):
            bank_account.configure(
                entity_slug=setup["entity_model"].slug,
                user_model=None,
                commit=True,
            )
