"""High-level API behavior tests for EntityModel closing entry wrappers."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io.io_core import get_localdate
from django_ledger.io.roles import ASSET_CA_CASH, CREDIT, DEBIT, EXPENSE_OPERATIONAL
from django_ledger.models import ClosingEntryModel, TransactionModel
from django_ledger.models.entity import EntityModel, EntityModelValidationError


class EntityClosingEntryHighLevelAPITest(TestCase):
    """
    High-level behavior tests for EntityModel closing-entry APIs.

    These tests keep setup deterministic and avoid cache/queryset helpers that
    currently depend on separately characterized closing-entry transaction bugs.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_entity_closing_entry_user",
            email="api-entity-closing-entry-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(
        self,
        *,
        name="API Entity Closing Entry Contract Entity",
        fy_start_month=1,
    ):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=fy_start_month,
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

        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
            "expense_account": expense_account,
        }

    def make_timestamp(self, tx_date):
        if settings.USE_TZ:
            return datetime(tx_date.year, tx_date.month, tx_date.day, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(tx_date.year, tx_date.month, tx_date.day, 12, 0)

    def create_posted_activity(self, setup, *, tx_date=date(2025, 1, 15)):
        entity_model = setup["entity_model"]
        ledger_model = entity_model.create_ledger(
            name=f"API Closing Activity Ledger {tx_date.isoformat()}",
            ledger_xid=f"api-closing-activity-{tx_date.isoformat()}",
            posted=True,
        )

        journal_entry, tx_models = entity_model.commit_txs(
            je_timestamp=self.make_timestamp(tx_date),
            je_ledger_model=ledger_model,
            je_posted=True,
            je_desc=f"API Closing Activity {tx_date.isoformat()}",
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

        self.assertTrue(ledger_model.posted)
        self.assertTrue(journal_entry.posted)
        self.assertEqual(len(tx_models), 2)

        return ledger_model, journal_entry, tx_models

    def create_posted_closing_entry(self, entity_model, closing_date):
        closing_entry = ClosingEntryModel.objects.create(
            entity_model=entity_model,
            closing_date=closing_date,
            posted=True,
        )
        closing_entry.refresh_from_db()
        return closing_entry

    def assert_closing_transactions_match_activity(self, ce_txs, setup):
        self.assertEqual(len(ce_txs), 2)
        self.assertEqual(
            {ce_tx.account_model_id for ce_tx in ce_txs},
            {setup["cash_account"].uuid, setup["expense_account"].uuid},
        )

        cash_tx = next(ce_tx for ce_tx in ce_txs if ce_tx.account_model_id == setup["cash_account"].uuid)
        expense_tx = next(ce_tx for ce_tx in ce_txs if ce_tx.account_model_id == setup["expense_account"].uuid)

        self.assertEqual(cash_tx.tx_type, CREDIT)
        self.assertEqual(cash_tx.balance, Decimal("100.00"))
        self.assertEqual(expense_tx.tx_type, DEBIT)
        self.assertEqual(expense_tx.balance, Decimal("100.00"))

    def test_get_closing_entry_digest_for_date_builds_transactions_from_posted_activity(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        self.create_posted_activity(setup, tx_date=date(2025, 1, 15))

        closing_entry, ce_txs = entity_model.get_closing_entry_digest_for_date(
            closing_date=date(2025, 1, 31),
        )

        self.assertEqual(closing_entry.entity_model_id, entity_model.uuid)
        self.assertEqual(closing_entry.closing_date, date(2025, 1, 31))
        self.assert_closing_transactions_match_activity(ce_txs, setup)

    def test_get_closing_entry_digest_for_month_uses_calendar_month_end(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        self.create_posted_activity(setup, tx_date=date(2025, 2, 15))

        closing_entry, ce_txs = entity_model.get_closing_entry_digest_for_month(
            year=2025,
            month=2,
        )

        self.assertEqual(closing_entry.closing_date, date(2025, 2, 28))
        self.assert_closing_transactions_match_activity(ce_txs, setup)

    def test_get_closing_entry_digest_for_fiscal_year_uses_entity_fiscal_year_end(self):
        setup = self.create_entity_setup(
            name="API Entity Closing Entry Fiscal Digest Entity",
            fy_start_month=4,
        )
        entity_model = setup["entity_model"]
        self.create_posted_activity(setup, tx_date=date(2026, 3, 15))

        closing_entry, ce_txs = entity_model.get_closing_entry_digest_for_fiscal_year(
            fiscal_year=2025,
        )

        self.assertEqual(closing_entry.closing_date, date(2026, 3, 31))
        self.assert_closing_transactions_match_activity(ce_txs, setup)

    def test_create_closing_entry_for_date_persists_entry_and_transactions(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        self.create_posted_activity(setup, tx_date=date(2025, 1, 15))

        closing_entry, ce_txs = entity_model.create_closing_entry_for_date(
            closing_date=date(2025, 1, 31),
        )
        closing_entry.refresh_from_db()

        self.assertEqual(closing_entry.entity_model_id, entity_model.uuid)
        self.assertEqual(closing_entry.closing_date, date(2025, 1, 31))
        self.assertFalse(closing_entry.posted)
        self.assertIsNotNone(closing_entry.ledger_model_id)
        self.assertEqual(closing_entry.closingentrytransactionmodel_set.count(), 2)
        self.assert_closing_transactions_match_activity(ce_txs, setup)

    def test_create_closing_entry_for_month_uses_month_end_date(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        self.create_posted_activity(setup, tx_date=date(2025, 2, 15))

        closing_entry, ce_txs = entity_model.create_closing_entry_for_month(
            year=2025,
            month=2,
        )

        self.assertEqual(closing_entry.closing_date, date(2025, 2, 28))
        self.assert_closing_transactions_match_activity(ce_txs, setup)

    def test_create_closing_entry_for_fiscal_year_uses_entity_fiscal_year_end(self):
        setup = self.create_entity_setup(
            name="API Entity Closing Entry Fiscal Year Entity",
            fy_start_month=4,
        )
        entity_model = setup["entity_model"]
        self.create_posted_activity(setup, tx_date=date(2025, 3, 15))

        closing_entry, ce_txs = entity_model.create_closing_entry_for_fiscal_year(
            fiscal_year=2024,
        )

        self.assertEqual(closing_entry.closing_date, date(2025, 3, 31))
        self.assert_closing_transactions_match_activity(ce_txs, setup)

    def test_close_entity_books_posts_entry_and_updates_closing_metadata(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        self.create_posted_activity(setup, tx_date=date(2025, 1, 15))

        closing_entry, ce_txs = entity_model.close_entity_books(
            closing_date=date(2025, 1, 31),
        )
        persisted_entity = EntityModel.objects.get(uuid=entity_model.uuid)
        closing_entry.refresh_from_db()

        self.assertTrue(closing_entry.posted)
        self.assertEqual(closing_entry.closing_date, date(2025, 1, 31))
        self.assertEqual(persisted_entity.last_closing_date, date(2025, 1, 31))
        self.assertEqual(persisted_entity.fetch_closing_entry_dates_meta(), [date(2025, 1, 31)])
        self.assertEqual(persisted_entity.fetch_closing_entry_dates_meta(as_date=False), ["2025-01-31"])
        self.assert_closing_transactions_match_activity(ce_txs, setup)

    def test_close_entity_books_refreshes_same_instance_closing_date_cache(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        self.create_posted_activity(setup, tx_date=date(2025, 1, 15))

        self.assertEqual(entity_model.fetch_closing_entry_dates_meta(), [])

        closing_entry, _ce_txs = entity_model.close_entity_books(
            closing_date=date(2025, 1, 31),
        )
        closing_entry.refresh_from_db()

        self.assertTrue(closing_entry.posted)
        self.assertEqual(entity_model.last_closing_date, date(2025, 1, 31))
        self.assertEqual(
            entity_model.meta[entity_model.META_KEY_CLOSING_ENTRY_DATES],
            ["2025-01-31"],
        )
        self.assertEqual(entity_model.fetch_closing_entry_dates_meta(), [date(2025, 1, 31)])

    def test_close_books_for_month_uses_month_end(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        self.create_posted_activity(setup, tx_date=date(2025, 2, 15))

        closing_entry, ce_txs = entity_model.close_books_for_month(
            year=2025,
            month=2,
        )

        self.assertTrue(closing_entry.posted)
        self.assertEqual(closing_entry.closing_date, date(2025, 2, 28))
        self.assert_closing_transactions_match_activity(ce_txs, setup)

    def test_close_books_for_fiscal_year_uses_non_calendar_fiscal_year_end(self):
        setup = self.create_entity_setup(
            name="API Entity Close Books Fiscal Year Entity",
            fy_start_month=4,
        )
        entity_model = setup["entity_model"]
        self.create_posted_activity(setup, tx_date=date(2025, 3, 15))

        closing_entry, ce_txs = entity_model.close_books_for_fiscal_year(
            fiscal_year=2024,
        )

        self.assertTrue(closing_entry.posted)
        self.assertEqual(closing_entry.closing_date, date(2025, 3, 31))
        self.assert_closing_transactions_match_activity(ce_txs, setup)

    def test_closing_entry_date_lookup_helpers_use_saved_metadata(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]

        self.create_posted_closing_entry(entity_model, closing_date=date(2025, 6, 30))
        self.create_posted_closing_entry(entity_model, closing_date=date(2025, 12, 31))

        saved_dates = entity_model.save_closing_entry_dates_meta(commit=True)
        entity_model.refresh_from_db()

        self.assertEqual(saved_dates, [date(2025, 12, 31), date(2025, 6, 30)])
        self.assertEqual(entity_model.last_closing_date, date(2025, 12, 31))
        self.assertEqual(
            entity_model.fetch_closing_entry_dates_meta(),
            [date(2025, 12, 31), date(2025, 6, 30)],
        )
        self.assertEqual(
            entity_model.fetch_closing_entry_dates_meta(as_date=False),
            ["2025-12-31", "2025-06-30"],
        )
        self.assertEqual(
            entity_model.get_closing_entry_for_date(date(2025, 12, 31)),
            date(2025, 12, 31),
        )
        self.assertEqual(
            entity_model.get_closing_entry_for_date(datetime(2025, 7, 1, 9, 0), inclusive=False),
            date(2025, 6, 30),
        )
        self.assertEqual(
            entity_model.get_nearest_next_closing_entry(date(2026, 1, 15)),
            date(2025, 12, 31),
        )
        self.assertEqual(
            entity_model.get_nearest_next_closing_entry(date(2025, 9, 1)),
            date(2025, 6, 30),
        )

    def test_close_entity_books_validates_required_arguments(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        closing_entry = ClosingEntryModel(
            entity_model=entity_model,
            closing_date=date(2025, 1, 31),
        )

        with self.assertRaises(EntityModelValidationError):
            entity_model.close_entity_books()

        with self.assertRaises(EntityModelValidationError):
            entity_model.close_entity_books(
                closing_date=date(2025, 1, 31),
                closing_entry_model=closing_entry,
            )

    def test_create_closing_entry_for_date_rejects_future_date(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]

        with self.assertRaises(EntityModelValidationError):
            entity_model.create_closing_entry_for_date(
                closing_date=get_localdate() + timedelta(days=1),
            )
