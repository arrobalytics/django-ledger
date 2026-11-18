"""
High-level API tests for ClosingEntryModel lifecycle behavior.
"""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io.roles import ASSET_CA_CASH, CREDIT, DEBIT, EXPENSE_OPERATIONAL
from django_ledger.models import TransactionModel
from django_ledger.models.closing_entry import (
    ClosingEntryModel,
    ClosingEntryTransactionModel,
    ClosingEntryValidationError,
)
from django_ledger.models.entity import EntityModel
from django_ledger.models.journal_entry import JournalEntryModel


class ClosingEntryLifecycleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_closing_entry_lifecycle_user",
            email="api-closing-entry-lifecycle-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self, tx_date):
        if settings.USE_TZ:
            return datetime(tx_date.year, tx_date.month, tx_date.day, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(tx_date.year, tx_date.month, tx_date.day, 12, 0)

    def create_entity_setup(self, *, name="API Closing Entry Lifecycle Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        entity_model.refresh_from_db()

        cash_account = entity_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
        )
        expense_account = entity_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=True,
        )
        equity_account = entity_model.create_account(
            code="3010",
            name=f"{name} Equity Account",
            role="eq_capital",
            balance_type=CREDIT,
            active=True,
        )

        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
            "expense_account": expense_account,
            "equity_account": equity_account,
        }

    def create_closing_entry(self, setup, *, closing_date=date(2025, 12, 31)):
        closing_entry = ClosingEntryModel.objects.create(
            entity_model=setup["entity_model"],
            closing_date=closing_date,
        )
        closing_entry.refresh_from_db()
        return closing_entry

    def create_balanced_closing_transactions(self, closing_entry, setup):
        ClosingEntryTransactionModel.objects.create(
            closing_entry_model=closing_entry,
            account_model=setup["cash_account"],
            tx_type=TransactionModel.DEBIT,
            balance=Decimal("100.00"),
        )
        ClosingEntryTransactionModel.objects.create(
            closing_entry_model=closing_entry,
            account_model=setup["equity_account"],
            tx_type=TransactionModel.CREDIT,
            balance=Decimal("100.00"),
        )

    def create_posted_activity(self, setup, *, tx_date=date(2025, 1, 15)):
        entity_model = setup["entity_model"]
        ledger_model = entity_model.create_ledger(
            name=f"API Closing Lifecycle Activity Ledger {tx_date.isoformat()}",
            ledger_xid=f"api-closing-lifecycle-activity-{tx_date.isoformat()}",
            posted=True,
        )
        journal_entry, tx_models = entity_model.commit_txs(
            je_timestamp=self.make_timestamp(tx_date),
            je_ledger_model=ledger_model,
            je_posted=True,
            je_desc=f"API Closing Lifecycle Activity {tx_date.isoformat()}",
            je_txs=[
                {
                    "account": setup["expense_account"],
                    "amount": Decimal("100.00"),
                    "tx_type": TransactionModel.DEBIT,
                    "description": "API expense debit.",
                },
                {
                    "account": setup["cash_account"],
                    "amount": Decimal("100.00"),
                    "tx_type": TransactionModel.CREDIT,
                    "description": "API cash credit.",
                },
            ],
        )
        journal_entry.refresh_from_db()
        ledger_model.refresh_from_db()
        self.assertTrue(journal_entry.posted)
        self.assertEqual(len(tx_models), 2)
        return ledger_model, journal_entry, tx_models

    def assert_generated_closing_entries(self, closing_entry):
        journal_entries = JournalEntryModel.objects.filter(
            ledger=closing_entry.ledger_model,
            is_closing_entry=True,
            origin="closing_entry",
        )
        self.assertEqual(journal_entries.count(), 1)
        journal_entry = journal_entries.get()
        self.assertTrue(journal_entry.posted)
        self.assertTrue(journal_entry.locked)
        self.assertEqual(journal_entry.timestamp, closing_entry.get_closing_date_as_timestamp())
        self.assertEqual(TransactionModel.objects.filter(journal_entry=journal_entry).count(), 2)

    def test_mark_as_posted_commit_true_posts_and_migrates_closing_records(self):
        setup = self.create_entity_setup()
        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_transactions(closing_entry, setup)

        closing_entry.mark_as_posted(commit=True, update_entity_meta=False)
        closing_entry.refresh_from_db()

        self.assertTrue(closing_entry.posted)
        self.assertFalse(closing_entry.can_post())
        self.assertTrue(closing_entry.can_unpost())
        self.assertFalse(closing_entry.can_update_txs())
        self.assertFalse(closing_entry.can_delete())
        self.assert_generated_closing_entries(closing_entry)
        closing_entry.ledger_model.refresh_from_db()
        self.assertTrue(closing_entry.ledger_model.posted)
        self.assertTrue(closing_entry.ledger_model.locked)

    def test_mark_as_posted_commit_false_still_migrates_and_locks_ledger_but_does_not_persist_entry_posted_flag(self):
        setup = self.create_entity_setup(name="API Closing Lifecycle Post False Entity")
        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_transactions(closing_entry, setup)

        closing_entry.mark_as_posted(commit=False, update_entity_meta=False)

        self.assertTrue(closing_entry.posted)
        persisted_closing_entry = ClosingEntryModel.objects.get(uuid=closing_entry.uuid)
        self.assertFalse(persisted_closing_entry.posted)
        self.assert_generated_closing_entries(closing_entry)
        closing_entry.ledger_model.refresh_from_db()
        self.assertTrue(closing_entry.ledger_model.locked)

    def test_mark_as_unposted_commit_true_removes_generated_records_and_unlocks_but_keeps_ledger_posted(self):
        setup = self.create_entity_setup(name="API Closing Lifecycle Unpost True Entity")
        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_transactions(closing_entry, setup)
        closing_entry.mark_as_posted(commit=True, update_entity_meta=False)

        closing_entry.mark_as_unposted(commit=True, update_entity_meta=False)
        closing_entry.refresh_from_db()

        self.assertFalse(closing_entry.posted)
        self.assertTrue(closing_entry.can_post())
        self.assertTrue(closing_entry.can_update_txs())
        self.assertFalse(JournalEntryModel.objects.filter(ledger=closing_entry.ledger_model).exists())
        self.assertFalse(TransactionModel.objects.filter(journal_entry__ledger=closing_entry.ledger_model).exists())
        closing_entry.ledger_model.refresh_from_db()
        self.assertTrue(closing_entry.ledger_model.posted)
        self.assertFalse(closing_entry.ledger_model.locked)

    def test_mark_as_unposted_commit_false_removes_generated_records_but_does_not_persist_entry_posted_flag(self):
        setup = self.create_entity_setup(name="API Closing Lifecycle Unpost False Entity")
        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_transactions(closing_entry, setup)
        closing_entry.mark_as_posted(commit=True, update_entity_meta=False)
        closing_entry.refresh_from_db()

        closing_entry.mark_as_unposted(commit=False, update_entity_meta=False)

        self.assertFalse(closing_entry.posted)
        persisted_closing_entry = ClosingEntryModel.objects.get(uuid=closing_entry.uuid)
        self.assertTrue(persisted_closing_entry.posted)
        self.assertFalse(JournalEntryModel.objects.filter(ledger=closing_entry.ledger_model).exists())
        closing_entry.ledger_model.refresh_from_db()
        self.assertTrue(closing_entry.ledger_model.posted)
        self.assertFalse(closing_entry.ledger_model.locked)

    def test_direct_post_and_unpost_with_entity_meta_refreshes_last_closing_date(self):
        setup = self.create_entity_setup(name="API Closing Lifecycle Entity Meta Entity")
        entity_model = setup["entity_model"]
        first_entry = self.create_closing_entry(setup, closing_date=date(2025, 6, 30))
        second_entry = self.create_closing_entry(setup, closing_date=date(2025, 12, 31))
        self.create_balanced_closing_transactions(first_entry, setup)
        self.create_balanced_closing_transactions(second_entry, setup)

        first_entry.mark_as_posted(commit=True, update_entity_meta=True)
        second_entry.mark_as_posted(commit=True, update_entity_meta=True)
        persisted_entity = EntityModel.objects.get(uuid=entity_model.uuid)

        self.assertEqual(persisted_entity.last_closing_date, date(2025, 12, 31))
        self.assertEqual(
            persisted_entity.fetch_closing_entry_dates_meta(),
            [date(2025, 12, 31), date(2025, 6, 30)],
        )

        second_entry.mark_as_unposted(commit=True, update_entity_meta=True)
        persisted_entity = EntityModel.objects.get(uuid=entity_model.uuid)

        self.assertEqual(persisted_entity.last_closing_date, date(2025, 6, 30))
        self.assertEqual(persisted_entity.fetch_closing_entry_dates_meta(), [date(2025, 6, 30)])

    def test_update_transactions_delegates_to_entity_close_behavior_without_posting_when_requested(self):
        setup = self.create_entity_setup(name="API Closing Lifecycle Update Transactions Entity")
        self.create_posted_activity(setup, tx_date=date(2025, 1, 15))
        closing_entry = self.create_closing_entry(setup, closing_date=date(2025, 1, 31))

        closing_entry.update_transactions(post_closing_entry=False)
        closing_entry.refresh_from_db()

        self.assertFalse(closing_entry.posted)
        self.assertEqual(closing_entry.closingentrytransactionmodel_set.count(), 2)
        self.assertFalse(JournalEntryModel.objects.filter(ledger=closing_entry.ledger_model).exists())

    def test_single_sided_closing_transactions_raise_domain_validation_error(self):
        setup = self.create_entity_setup(name="API Closing Lifecycle Single Sided Entity")
        closing_entry = self.create_closing_entry(setup)
        ClosingEntryTransactionModel.objects.create(
            closing_entry_model=closing_entry,
            account_model=setup["cash_account"],
            tx_type=TransactionModel.DEBIT,
            balance=Decimal("100.00"),
        )

        with self.assertRaises(ClosingEntryValidationError):
            closing_entry.mark_as_posted(commit=True, update_entity_meta=False)
