"""
High-level API behavior tests for BankAccountModel lifecycle helpers.

These tests cover direct active/hidden state helpers without data import or
staged transaction behavior.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT
from django_ledger.models import BankAccountModel
from django_ledger.models.bank_account import BankAccountValidationError
from django_ledger.models.entity import EntityModel


class BankAccountLifecycleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_bank_account_lifecycle_user",
            email="api-bank-account-lifecycle-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Bank Account Lifecycle Entity"):
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
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
        }

    def create_bank_account(
        self,
        setup,
        *,
        name="API Bank Account Lifecycle Account",
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

    def test_active_predicates_reflect_current_active_state(self):
        setup = self.create_entity_setup()
        inactive_bank_account = self.create_bank_account(
            setup,
            name="API Inactive Predicate Bank Account",
            active=False,
        )
        active_bank_account = self.create_bank_account(
            setup,
            name="API Active Predicate Bank Account",
            account_number="000987654321",
            routing_number="000222000",
            active=True,
        )

        self.assertFalse(inactive_bank_account.is_active())
        self.assertTrue(inactive_bank_account.can_activate())
        self.assertFalse(inactive_bank_account.can_inactivate())

        self.assertTrue(active_bank_account.is_active())
        self.assertFalse(active_bank_account.can_activate())
        self.assertTrue(active_bank_account.can_inactivate())

    def test_mark_as_active_commit_false_updates_only_in_memory_state(self):
        setup = self.create_entity_setup(name="API Bank Account Active Commit False Entity")
        bank_account = self.create_bank_account(setup, active=False)

        bank_account.mark_as_active(commit=False)

        self.assertTrue(bank_account.active)

        bank_account.refresh_from_db()
        self.assertFalse(bank_account.active)

    def test_mark_as_active_commit_true_persists_active_state(self):
        setup = self.create_entity_setup(name="API Bank Account Active Commit True Entity")
        bank_account = self.create_bank_account(setup, active=False)

        bank_account.mark_as_active(commit=True)

        bank_account.refresh_from_db()
        self.assertTrue(bank_account.active)

    def test_mark_as_inactive_commit_false_updates_only_in_memory_state(self):
        setup = self.create_entity_setup(name="API Bank Account Inactive Commit False Entity")
        bank_account = self.create_bank_account(setup, active=True)

        bank_account.mark_as_inactive(commit=False)

        self.assertFalse(bank_account.active)

        bank_account.refresh_from_db()
        self.assertTrue(bank_account.active)

    def test_mark_as_inactive_commit_true_persists_inactive_state(self):
        setup = self.create_entity_setup(name="API Bank Account Inactive Commit True Entity")
        bank_account = self.create_bank_account(setup, active=True)

        bank_account.mark_as_inactive(commit=True)

        bank_account.refresh_from_db()
        self.assertFalse(bank_account.active)

    def test_invalid_active_transitions_with_raise_exception_true_raise_validation_error(self):
        setup = self.create_entity_setup(name="API Bank Account Invalid Raise Entity")
        active_bank_account = self.create_bank_account(
            setup,
            name="API Already Active Bank Account",
            active=True,
        )
        inactive_bank_account = self.create_bank_account(
            setup,
            name="API Already Inactive Bank Account",
            account_number="000987654321",
            routing_number="000222000",
            active=False,
        )

        with self.assertRaises(BankAccountValidationError):
            active_bank_account.mark_as_active(commit=True)

        with self.assertRaises(BankAccountValidationError):
            inactive_bank_account.mark_as_inactive(commit=True)

    def test_invalid_active_transitions_with_raise_exception_false_are_noops(self):
        setup = self.create_entity_setup(name="API Bank Account Invalid Noop Entity")
        active_bank_account = self.create_bank_account(
            setup,
            name="API Already Active Noop Bank Account",
            active=True,
        )
        inactive_bank_account = self.create_bank_account(
            setup,
            name="API Already Inactive Noop Bank Account",
            account_number="000987654321",
            routing_number="000222000",
            active=False,
        )

        active_bank_account.mark_as_active(commit=True, raise_exception=False)
        inactive_bank_account.mark_as_inactive(commit=True, raise_exception=False)

        active_bank_account.refresh_from_db()
        inactive_bank_account.refresh_from_db()

        self.assertTrue(active_bank_account.active)
        self.assertFalse(inactive_bank_account.active)

    def test_hidden_predicates_reflect_current_hidden_state(self):
        setup = self.create_entity_setup(name="API Bank Account Hidden Predicate Entity")
        visible_bank_account = self.create_bank_account(
            setup,
            name="API Visible Bank Account",
            hidden=False,
        )
        hidden_bank_account = self.create_bank_account(
            setup,
            name="API Hidden Bank Account",
            account_number="000987654321",
            routing_number="000222000",
            hidden=True,
        )

        self.assertTrue(visible_bank_account.can_hide())
        self.assertFalse(visible_bank_account.can_unhide())

        self.assertFalse(hidden_bank_account.can_hide())
        self.assertTrue(hidden_bank_account.can_unhide())
