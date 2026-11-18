"""
High-level API behavior tests for TransactionModel date and status filters.

These tests cover date boundaries, closing-entry filters, and cleared/
reconciled status filters without exercising relation or URL helpers.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel


class TransactionDateStatusAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_tx_date_status_admin",
            email="api-tx-date-status-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self, year=2026, month=1, day=15, hour=12):
        if settings.USE_TZ:
            return datetime(year, month, day, hour, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(year, month, day, hour, 0)

    def create_entity_setup(self, *, name="API Transaction Date Status Entity"):
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
            "expense_account": expense_account,
            "ledger_model": ledger_model,
        }

    def create_journal_entry(
        self,
        ledger_model,
        *,
        description="API Transaction Date Status Journal Entry",
        timestamp=None,
        is_closing_entry=False,
    ):
        return JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=timestamp if timestamp is not None else self.make_timestamp(),
            description=description,
            is_closing_entry=is_closing_entry,
        )

    def create_transaction(
        self,
        setup,
        *,
        description="API Transaction Date Status Transaction",
        timestamp=None,
        is_closing_entry=False,
        cleared=False,
        reconciled=False,
    ):
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description=f"{description} Journal Entry",
            timestamp=timestamp,
            is_closing_entry=is_closing_entry,
        )
        return TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=setup["expense_account"],
            amount=Decimal("10.00"),
            description=description,
            cleared=cleared,
            reconciled=reconciled,
        )

    def transaction_ids(self, queryset):
        return set(queryset.values_list("uuid", flat=True))

    def test_from_date_filters_date_datetime_and_iso_string_inclusively(self):
        setup = self.create_entity_setup(name="API TX From Date Entity")
        before_tx = self.create_transaction(
            setup,
            description="API TX Before From Date",
            timestamp=self.make_timestamp(2026, 1, 14),
        )
        boundary_tx = self.create_transaction(
            setup,
            description="API TX Boundary From Date",
            timestamp=self.make_timestamp(2026, 1, 15),
        )
        after_tx = self.create_transaction(
            setup,
            description="API TX After From Date",
            timestamp=self.make_timestamp(2026, 1, 16),
        )
        expected_ids = {boundary_tx.uuid, after_tx.uuid}
        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"])

        for from_date in (
            self.make_timestamp(2026, 1, 15).date(),
            self.make_timestamp(2026, 1, 15),
            "2026-01-15",
        ):
            with self.subTest(from_date=from_date):
                filtered_qs = transaction_qs.from_date(from_date)

                self.assertEqual(expected_ids, self.transaction_ids(filtered_qs))
                self.assertNotIn(before_tx.uuid, self.transaction_ids(filtered_qs))

    def test_to_date_filters_date_datetime_and_iso_string_inclusively(self):
        setup = self.create_entity_setup(name="API TX To Date Entity")
        before_tx = self.create_transaction(
            setup,
            description="API TX Before To Date",
            timestamp=self.make_timestamp(2026, 1, 14),
        )
        boundary_tx = self.create_transaction(
            setup,
            description="API TX Boundary To Date",
            timestamp=self.make_timestamp(2026, 1, 15),
        )
        after_tx = self.create_transaction(
            setup,
            description="API TX After To Date",
            timestamp=self.make_timestamp(2026, 1, 16),
        )
        expected_ids = {before_tx.uuid, boundary_tx.uuid}
        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"])

        for to_date in (
            self.make_timestamp(2026, 1, 15).date(),
            self.make_timestamp(2026, 1, 15),
            "2026-01-15",
        ):
            with self.subTest(to_date=to_date):
                filtered_qs = transaction_qs.to_date(to_date)

                self.assertEqual(expected_ids, self.transaction_ids(filtered_qs))
                self.assertNotIn(after_tx.uuid, self.transaction_ids(filtered_qs))

    def test_closing_entry_filters_return_matching_transactions(self):
        setup = self.create_entity_setup(name="API TX Closing Filter Entity")
        closing_tx = self.create_transaction(
            setup,
            description="API TX Closing Entry",
            is_closing_entry=True,
        )
        regular_tx = self.create_transaction(
            setup,
            description="API TX Regular Entry",
            is_closing_entry=False,
        )
        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"])

        self.assertEqual({closing_tx.uuid}, self.transaction_ids(transaction_qs.is_closing_entry()))
        self.assertEqual({regular_tx.uuid}, self.transaction_ids(transaction_qs.not_closing_entry()))

    def test_cleared_filters_return_matching_transactions(self):
        setup = self.create_entity_setup(name="API TX Cleared Filter Entity")
        cleared_tx = self.create_transaction(
            setup,
            description="API TX Cleared",
            cleared=True,
        )
        uncleared_tx = self.create_transaction(
            setup,
            description="API TX Not Cleared",
            cleared=False,
        )
        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"])

        self.assertEqual({cleared_tx.uuid}, self.transaction_ids(transaction_qs.is_cleared()))
        self.assertEqual({uncleared_tx.uuid}, self.transaction_ids(transaction_qs.not_cleared()))

    def test_reconciled_filters_return_matching_transactions(self):
        setup = self.create_entity_setup(name="API TX Reconciled Filter Entity")
        reconciled_tx = self.create_transaction(
            setup,
            description="API TX Reconciled",
            reconciled=True,
        )
        unreconciled_tx = self.create_transaction(
            setup,
            description="API TX Not Reconciled",
            reconciled=False,
        )
        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"])

        self.assertEqual({reconciled_tx.uuid}, self.transaction_ids(transaction_qs.is_reconciled()))
        self.assertEqual({unreconciled_tx.uuid}, self.transaction_ids(transaction_qs.not_reconciled()))
