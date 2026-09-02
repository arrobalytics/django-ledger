"""
Smoke tests for JournalEntryModel lifecycle signals.

These tests verify that public lifecycle methods emit their corresponding
signals without asserting unrelated payload details.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.signals import (
    journal_entry_locked,
    journal_entry_posted,
    journal_entry_unlocked,
    journal_entry_unposted,
)


class JournalEntrySignalsAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_je_signals_admin",
            email="api-je-signals-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_with_accounting_setup(self, *, name="API JE Signals Entity"):
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
        description="API JE Signals Journal Entry",
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

    def collect_signal_calls(self, signal):
        calls = []
        dispatch_uid = f"{self.id()}-{id(signal)}"

        def receiver(sender, **kwargs):
            calls.append(kwargs)

        signal.connect(
            receiver,
            sender=JournalEntryModel,
            weak=False,
            dispatch_uid=dispatch_uid,
        )
        self.addCleanup(
            signal.disconnect,
            sender=JournalEntryModel,
            dispatch_uid=dispatch_uid,
        )
        return calls

    def assert_signal_received_once(self, calls, journal_entry, *, commit):
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["instance"], journal_entry)
        self.assertEqual(calls[0]["commited"], commit)

    def test_mark_as_posted_emits_journal_entry_posted_signal(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Posted Signal Entity",
        )
        journal_entry = self.create_balanced_journal_entry(
            setup,
            description="API JE Posted Signal",
            locked=True,
        )
        calls = self.collect_signal_calls(journal_entry_posted)

        journal_entry.mark_as_posted(commit=True)

        self.assert_signal_received_once(calls, journal_entry, commit=True)

    def test_mark_as_unposted_emits_journal_entry_unposted_signal(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Unposted Signal Entity",
        )
        journal_entry = self.create_balanced_journal_entry(
            setup,
            description="API JE Unposted Signal",
            locked=True,
        )
        journal_entry.mark_as_posted(commit=True)
        calls = self.collect_signal_calls(journal_entry_unposted)

        journal_entry.mark_as_unposted(commit=True)

        self.assert_signal_received_once(calls, journal_entry, commit=True)

    def test_mark_as_locked_emits_journal_entry_locked_signal(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Locked Signal Entity",
        )
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Locked Signal",
            locked=False,
        )
        calls = self.collect_signal_calls(journal_entry_locked)

        journal_entry.mark_as_locked(commit=True)

        self.assert_signal_received_once(calls, journal_entry, commit=True)

    def test_mark_as_unlocked_emits_journal_entry_unlocked_signal(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Unlocked Signal Entity",
        )
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Unlocked Signal",
            locked=True,
        )
        calls = self.collect_signal_calls(journal_entry_unlocked)

        journal_entry.mark_as_unlocked(commit=True)

        self.assert_signal_received_once(calls, journal_entry, commit=True)
