"""
High-level API behavior tests for LedgerModel journal-entry batch helpers.

These tests cover public batch posting and locking behavior without exercising
signals.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel


class LedgerJournalEntryBatchAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_ledger_je_batch_admin",
            email="api-ledger-je-batch-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_with_accounting_setup(self, *, name="API Ledger JE Batch Entity"):
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
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "expense_account": expense_account,
            "ledger_model": ledger_model,
        }

    def create_journal_entry(
        self,
        ledger_model,
        *,
        description="API Ledger JE Batch Journal Entry",
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

    def create_postable_journal_entry(self, setup, *, description):
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description=description,
            posted=False,
            locked=False,
        )
        self.add_balanced_transactions(
            journal_entry,
            cash_account=setup["cash_account"],
            expense_account=setup["expense_account"],
        )
        journal_entry.locked = True
        journal_entry.save(update_fields=["locked", "updated"])
        return journal_entry

    def test_post_journal_entries_commit_false_posts_unposted_entries_in_memory_only(self):
        setup = self.create_entity_with_accounting_setup(
            name="API Ledger JE Batch Post Commit False Entity"
        )
        journal_entry = self.create_postable_journal_entry(
            setup,
            description="API Batch Post Commit False JE",
        )

        posted_entries = list(setup["ledger_model"].post_journal_entries(commit=False))

        self.assertEqual([journal_entry.uuid], [entry.uuid for entry in posted_entries])
        self.assertTrue(posted_entries[0].posted)

        journal_entry.refresh_from_db()
        self.assertFalse(journal_entry.posted)

    def test_post_journal_entries_commit_true_persists_posted_state(self):
        setup = self.create_entity_with_accounting_setup(
            name="API Ledger JE Batch Post Commit True Entity"
        )
        journal_entry = self.create_postable_journal_entry(
            setup,
            description="API Batch Post Commit True JE",
        )

        posted_entries = list(setup["ledger_model"].post_journal_entries(commit=True))

        self.assertEqual([journal_entry.uuid], [entry.uuid for entry in posted_entries])

        journal_entry.refresh_from_db()
        self.assertTrue(journal_entry.posted)

    def test_post_journal_entries_does_not_change_already_posted_entries(self):
        setup = self.create_entity_with_accounting_setup(
            name="API Ledger JE Batch Already Posted Entity"
        )
        posted_journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API Batch Already Posted JE",
            posted=True,
            locked=False,
            force_create=True,
        )
        unposted_journal_entry = self.create_postable_journal_entry(
            setup,
            description="API Batch Newly Posted JE",
        )

        posted_entries = list(setup["ledger_model"].post_journal_entries(commit=True))

        self.assertEqual([unposted_journal_entry.uuid], [entry.uuid for entry in posted_entries])

        posted_journal_entry.refresh_from_db()
        self.assertTrue(posted_journal_entry.posted)
        self.assertFalse(posted_journal_entry.locked)

    def test_lock_journal_entries_commit_false_locks_unlocked_entries_in_memory_only(self):
        setup = self.create_entity_with_accounting_setup(
            name="API Ledger JE Batch Lock Commit False Entity"
        )
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API Batch Lock Commit False JE",
            posted=False,
            locked=False,
        )

        locked_entries = list(setup["ledger_model"].lock_journal_entries(commit=False))

        self.assertEqual([journal_entry.uuid], [entry.uuid for entry in locked_entries])
        self.assertTrue(locked_entries[0].locked)

        journal_entry.refresh_from_db()
        self.assertFalse(journal_entry.locked)

    def test_lock_journal_entries_commit_true_persists_locked_state(self):
        setup = self.create_entity_with_accounting_setup(
            name="API Ledger JE Batch Lock Commit True Entity"
        )
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API Batch Lock Commit True JE",
            posted=False,
            locked=False,
        )

        locked_entries = list(setup["ledger_model"].lock_journal_entries(commit=True))

        self.assertEqual([journal_entry.uuid], [entry.uuid for entry in locked_entries])

        journal_entry.refresh_from_db()
        self.assertTrue(journal_entry.locked)

    def test_lock_journal_entries_does_not_change_already_locked_entries(self):
        setup = self.create_entity_with_accounting_setup(
            name="API Ledger JE Batch Already Locked Entity"
        )
        locked_journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API Batch Already Locked JE",
            posted=False,
            locked=True,
        )
        unlocked_journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API Batch Newly Locked JE",
            posted=False,
            locked=False,
        )

        locked_entries = list(setup["ledger_model"].lock_journal_entries(commit=True))

        self.assertEqual([unlocked_journal_entry.uuid], [entry.uuid for entry in locked_entries])

        locked_journal_entry.refresh_from_db()
        self.assertTrue(locked_journal_entry.locked)
