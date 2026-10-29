"""
High-level API behavior tests for AccountModel lifecycle transitions.

These tests cover direct public state changes without queryset, URL, or model
property assertions.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT
from django_ledger.models.accounts import AccountModelValidationError
from django_ledger.models.entity import EntityModel


class AccountLifecycleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_account_lifecycle_user",
            email="api-account-lifecycle-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Account Lifecycle Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_entity_with_default_coa(self, *, name="API Account Lifecycle Entity"):
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
        code="1010",
        name="API Account Lifecycle Cash",
        active=True,
        locked=False,
    ):
        account_model = coa_model.create_account(
            code=code,
            name=name,
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=active,
        )
        if locked:
            account_model.locked = True
            account_model.save(update_fields=["locked", "updated"])
        return account_model

    def test_activate_commit_false_updates_only_in_memory_state(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Activate Commit False Entity",
        )
        account_model = self.create_account(
            coa_model,
            code="1010",
            name="API Account Activate Commit False",
            active=False,
        )

        account_model.activate(commit=False)

        self.assertTrue(account_model.active)

        account_model.refresh_from_db()
        self.assertFalse(account_model.active)

    def test_activate_commit_true_persists_active_state(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Activate Commit True Entity",
        )
        account_model = self.create_account(
            coa_model,
            code="1010",
            name="API Account Activate Commit True",
            active=False,
        )

        account_model.activate(commit=True)

        account_model.refresh_from_db()
        self.assertTrue(account_model.active)

    def test_deactivate_commit_true_persists_inactive_state(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Deactivate Entity",
        )
        account_model = self.create_account(
            coa_model,
            code="1010",
            name="API Account Deactivate",
            active=True,
        )

        account_model.deactivate(commit=True)

        account_model.refresh_from_db()
        self.assertFalse(account_model.active)

    def test_lock_commit_false_updates_only_in_memory_state(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Lock Commit False Entity",
        )
        account_model = self.create_account(
            coa_model,
            code="1010",
            name="API Account Lock Commit False",
            locked=False,
        )

        account_model.lock(commit=False)

        self.assertTrue(account_model.locked)

        account_model.refresh_from_db()
        self.assertFalse(account_model.locked)

    def test_lock_commit_true_persists_locked_state(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Lock Commit True Entity",
        )
        account_model = self.create_account(
            coa_model,
            code="1010",
            name="API Account Lock Commit True",
            locked=False,
        )

        account_model.lock(commit=True)

        account_model.refresh_from_db()
        self.assertTrue(account_model.locked)

    def test_unlock_commit_true_persists_unlocked_state(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Unlock Entity",
        )
        account_model = self.create_account(
            coa_model,
            code="1010",
            name="API Account Unlock",
            locked=True,
        )

        account_model.unlock(commit=True)

        account_model.refresh_from_db()
        self.assertFalse(account_model.locked)

    def test_predicate_helpers_reflect_current_state(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Predicate Entity",
        )
        inactive_unlocked_account = self.create_account(
            coa_model,
            code="1010",
            name="API Account Inactive Unlocked",
            active=False,
            locked=False,
        )
        active_locked_account = self.create_account(
            coa_model,
            code="1020",
            name="API Account Active Locked",
            active=True,
            locked=True,
        )

        self.assertTrue(inactive_unlocked_account.can_activate())
        self.assertFalse(inactive_unlocked_account.can_deactivate())
        self.assertTrue(inactive_unlocked_account.can_lock())
        self.assertFalse(inactive_unlocked_account.can_unlock())

        self.assertFalse(active_locked_account.can_activate())
        self.assertTrue(active_locked_account.can_deactivate())
        self.assertFalse(active_locked_account.can_lock())
        self.assertTrue(active_locked_account.can_unlock())

    def test_invalid_transitions_with_raise_exception_false_are_noops(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Invalid Noop Entity",
        )
        active_account = self.create_account(
            coa_model,
            code="1010",
            name="API Account Already Active",
            active=True,
        )
        inactive_account = self.create_account(
            coa_model,
            code="1020",
            name="API Account Already Inactive",
            active=False,
        )
        locked_account = self.create_account(
            coa_model,
            code="1030",
            name="API Account Already Locked",
            locked=True,
        )
        unlocked_account = self.create_account(
            coa_model,
            code="1040",
            name="API Account Already Unlocked",
            locked=False,
        )

        active_account.activate(commit=True, raise_exception=False)
        inactive_account.deactivate(commit=True, raise_exception=False)
        locked_account.lock(commit=True, raise_exception=False)
        unlocked_account.unlock(commit=True, raise_exception=False)

        active_account.refresh_from_db()
        inactive_account.refresh_from_db()
        locked_account.refresh_from_db()
        unlocked_account.refresh_from_db()

        self.assertTrue(active_account.active)
        self.assertFalse(inactive_account.active)
        self.assertTrue(locked_account.locked)
        self.assertFalse(unlocked_account.locked)

    def test_invalid_transitions_with_raise_exception_true_raise_validation_error(self):
        _entity_model, coa_model = self.create_entity_with_default_coa(
            name="API Account Invalid Raise Entity",
        )
        active_account = self.create_account(
            coa_model,
            code="1010",
            name="API Account Active Invalid",
            active=True,
        )
        inactive_account = self.create_account(
            coa_model,
            code="1020",
            name="API Account Inactive Invalid",
            active=False,
        )
        locked_account = self.create_account(
            coa_model,
            code="1030",
            name="API Account Locked Invalid",
            locked=True,
        )
        unlocked_account = self.create_account(
            coa_model,
            code="1040",
            name="API Account Unlocked Invalid",
            locked=False,
        )

        with self.assertRaises(AccountModelValidationError):
            active_account.activate(commit=True)

        with self.assertRaises(AccountModelValidationError):
            inactive_account.deactivate(commit=True)

        with self.assertRaises(AccountModelValidationError):
            locked_account.lock(commit=True)

        with self.assertRaises(AccountModelValidationError):
            unlocked_account.unlock(commit=True)
