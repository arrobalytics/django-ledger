"""
High-level API behavior tests for BankAccountModel.configure().

These tests cover direct bank account configuration without queryset or data
import behavior.
"""

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT
from django_ledger.models import BankAccountModel
from django_ledger.models.bank_account import BankAccountValidationError
from django_ledger.models.entity import EntityModel


class BankAccountConfigureAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_bank_account_configure_admin",
            email="api-bank-account-configure-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_bank_account_configure_unrelated",
            email="api-bank-account-configure-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Bank Account Configure Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
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

    def make_bank_account(
        self,
        setup,
        *,
        name="API Bank Account Configure Account",
        account_number="000123456789",
        routing_number="000111000",
    ):
        return BankAccountModel(
            name=name,
            account_model=setup["cash_account"],
            account_number=account_number,
            routing_number=routing_number,
            active=True,
        )

    def test_configure_with_entity_model_binds_entity_and_preserves_account(self):
        setup = self.create_entity_setup(name="API Bank Account Configure Model Entity")
        bank_account = self.make_bank_account(setup)

        returned_bank_account, returned_entity = bank_account.configure(
            entity_slug=setup["entity_model"],
            user_model=None,
            commit=True,
        )

        bank_account.refresh_from_db()

        self.assertEqual(returned_bank_account, bank_account)
        self.assertEqual(returned_entity, setup["entity_model"])
        self.assertEqual(bank_account.entity_model_id, setup["entity_model"].uuid)
        self.assertEqual(bank_account.account_model_id, setup["cash_account"].uuid)

    def test_configure_with_slug_commit_false_updates_only_in_memory_state(self):
        setup = self.create_entity_setup(name="API Bank Account Configure Commit False Entity")
        bank_account = self.make_bank_account(setup)

        returned_bank_account, returned_entity = bank_account.configure(
            entity_slug=setup["entity_model"].slug,
            user_model=self.admin_user,
            commit=False,
        )

        self.assertEqual(returned_bank_account, bank_account)
        self.assertEqual(returned_entity, setup["entity_model"])
        self.assertEqual(bank_account.entity_model_id, setup["entity_model"].uuid)
        self.assertFalse(BankAccountModel.objects.filter(uuid=bank_account.uuid).exists())

    def test_configure_with_slug_commit_true_persists_entity_binding(self):
        setup = self.create_entity_setup(name="API Bank Account Configure Commit True Entity")
        bank_account = self.make_bank_account(setup)

        bank_account.configure(
            entity_slug=setup["entity_model"].slug,
            user_model=self.admin_user,
            commit=True,
        )

        bank_account.refresh_from_db()
        self.assertEqual(bank_account.entity_model_id, setup["entity_model"].uuid)
        self.assertEqual(bank_account.account_model_id, setup["cash_account"].uuid)

    def test_configure_with_slug_requires_user_model(self):
        setup = self.create_entity_setup(name="API Bank Account Configure Missing User Entity")
        bank_account = self.make_bank_account(setup)

        with self.assertRaises(BankAccountValidationError):
            bank_account.configure(
                entity_slug=setup["entity_model"].slug,
                user_model=None,
                commit=True,
            )

    def test_configure_with_slug_rejects_unrelated_user(self):
        setup = self.create_entity_setup(name="API Bank Account Configure Unrelated Entity")
        bank_account = self.make_bank_account(setup)

        with self.assertRaises(Http404):
            bank_account.configure(
                entity_slug=setup["entity_model"].slug,
                user_model=self.unrelated_user,
                commit=True,
            )

    def test_configure_rejects_invalid_entity_input(self):
        setup = self.create_entity_setup(name="API Bank Account Configure Invalid Entity")
        bank_account = self.make_bank_account(setup)

        with self.assertRaises(BankAccountValidationError):
            bank_account.configure(
                entity_slug=object(),
                user_model=self.admin_user,
                commit=True,
            )
