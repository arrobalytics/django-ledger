"""
High-level API behavior tests for JournalEntryModel lifecycle transitions.

These tests cover direct public state changes without locked-period or signal
behavior.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.journal_entry import JournalEntryValidationError


class JournalEntryLifecycleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_je_lifecycle_admin",
            email="api-je-lifecycle-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_with_accounting_setup(self, *, name="API JE Lifecycle Entity"):
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
            name=f"{name} Cash",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense",
            role="ex_regular",
            balance_type="debit",
            active=True,
        )
        ledger_model = LedgerModel.objects.create(
            name=f"{name} Ledger",
            ledger_xid=f"{name.lower().replace(' ', '-')}-ledger",
            entity=entity_model,
        )

        return {
            "cash_account": cash_account,
            "expense_account": expense_account,
            "ledger_model": ledger_model,
        }

    def create_journal_entry(
        self,
        ledger_model,
        *,
        description="API JE Lifecycle Journal Entry",
        posted=False,
        locked=False,
        force_create=False,
    ):
        create_kwargs = {
            "ledger": ledger_model,
            "timestamp": self.make_timestamp(),
            "description": description,
            "posted": posted,
            "locked": locked,
        }
        if force_create:
            create_kwargs["force_create"] = True
        return JournalEntryModel.objects.create(**create_kwargs)

    def add_balanced_transactions(self, journal_entry, *, cash_account, expense_account):
        TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=expense_account,
            amount=Decimal("100.00"),
            description="Expense debit.",
        )
        TransactionModel.objects.create(
            tx_type=TransactionModel.CREDIT,
            journal_entry=journal_entry,
            account=cash_account,
            amount=Decimal("100.00"),
            description="Cash credit.",
        )

    def create_balanced_journal_entry(self, setup, *, description, locked=False):
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description=description,
            locked=False,
        )
        self.add_balanced_transactions(
            journal_entry,
            cash_account=setup["cash_account"],
            expense_account=setup["expense_account"],
        )
        if locked:
            journal_entry.locked = True
            journal_entry.save(verify=False, update_fields=["locked", "updated"])
        return journal_entry

    def test_mark_as_locked_commit_false_updates_only_in_memory_state(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Lock Commit False Entity",
        )
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Lock Commit False",
        )

        journal_entry.mark_as_locked(commit=False)

        self.assertTrue(journal_entry.locked)

        journal_entry.refresh_from_db()
        self.assertFalse(journal_entry.locked)

    def test_lock_commit_true_persists_locked_state(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Lock Commit True Entity",
        )
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Lock Commit True",
        )

        journal_entry.lock(commit=True)

        journal_entry.refresh_from_db()
        self.assertTrue(journal_entry.locked)

    def test_unlock_commit_true_persists_unlocked_state_for_explicitly_locked_entry(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Unlock Commit True Entity",
        )
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Unlock Commit True",
            locked=True,
        )

        journal_entry.unlock(commit=True)

        journal_entry.refresh_from_db()
        self.assertFalse(journal_entry.locked)

    def test_mark_as_posted_commit_true_persists_posted_state_for_balanced_locked_entry(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Post Commit True Entity",
        )
        journal_entry = self.create_balanced_journal_entry(
            setup,
            description="API JE Post Commit True",
            locked=True,
        )

        journal_entry.mark_as_posted(commit=True)

        journal_entry.refresh_from_db()
        self.assertTrue(journal_entry.posted)
        self.assertTrue(journal_entry.has_activity())

    def test_unpost_commit_true_persists_unposted_state_and_clears_activity(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Unpost Commit True Entity",
        )
        journal_entry = self.create_balanced_journal_entry(
            setup,
            description="API JE Unpost Commit True",
            locked=True,
        )
        journal_entry.mark_as_posted(commit=True)

        journal_entry.refresh_from_db()
        self.assertTrue(journal_entry.posted)
        self.assertTrue(journal_entry.has_activity())

        journal_entry.unpost(commit=True)

        journal_entry.refresh_from_db()
        self.assertFalse(journal_entry.posted)
        self.assertIsNone(journal_entry.activity)

    def test_post_force_lock_commit_true_locks_and_posts_balanced_entry(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Force Lock Post Entity",
        )
        journal_entry = self.create_balanced_journal_entry(
            setup,
            description="API JE Force Lock Post",
            locked=False,
        )

        journal_entry.post(force_lock=True, commit=True)

        journal_entry.refresh_from_db()
        self.assertTrue(journal_entry.locked)
        self.assertTrue(journal_entry.posted)

    def test_invalid_transitions_with_raise_exception_false_are_noops(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Invalid No Raise Entity",
        )
        already_locked = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Already Locked",
            locked=True,
        )
        unlocked = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Already Unlocked",
            locked=False,
        )
        posted = self.create_balanced_journal_entry(
            setup,
            description="API JE Already Posted",
            locked=True,
        )
        posted.mark_as_posted(commit=True)
        unposted = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Already Unposted",
            posted=False,
        )

        already_locked.mark_as_locked(commit=True, raise_exception=False)
        unlocked.mark_as_unlocked(commit=True, raise_exception=False)
        posted.mark_as_posted(commit=True, raise_exception=False)
        unposted.mark_as_unposted(commit=True, raise_exception=False)

        already_locked.refresh_from_db()
        unlocked.refresh_from_db()
        posted.refresh_from_db()
        unposted.refresh_from_db()

        self.assertTrue(already_locked.locked)
        self.assertFalse(unlocked.locked)
        self.assertTrue(posted.posted)
        self.assertFalse(unposted.posted)

    def test_invalid_transitions_with_raise_exception_true_raise_validation_error(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Invalid Raise Entity",
        )
        already_locked = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Invalid Already Locked",
            locked=True,
        )
        unlocked = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Invalid Already Unlocked",
            locked=False,
        )
        posted = self.create_balanced_journal_entry(
            setup,
            description="API JE Invalid Already Posted",
            locked=True,
        )
        posted.mark_as_posted(commit=True)
        unposted = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Invalid Already Unposted",
            posted=False,
        )

        with self.assertRaises(JournalEntryValidationError):
            already_locked.mark_as_locked(commit=True, raise_exception=True)
        with self.assertRaises(JournalEntryValidationError):
            unlocked.mark_as_unlocked(commit=True, raise_exception=True)
        with self.assertRaises(JournalEntryValidationError):
            posted.mark_as_posted(commit=True, raise_exception=True)
        with self.assertRaises(JournalEntryValidationError):
            unposted.mark_as_unposted(commit=True, raise_exception=True)
