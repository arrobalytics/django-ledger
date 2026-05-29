"""
High-level API behavior tests for LedgerModel current and locked-period helpers.

These tests cover the public current-ledger queryset contract and locked-period
detection without exercising closing-entry creation.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel
from django_ledger.models.entity import EntityModel


class LedgerLockedPeriodAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_ledger_locked_period_admin",
            email="api-ledger-locked-period-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(
        self,
        *,
        name="API Ledger Locked Period Entity",
        last_closing_date=None,
    ):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        if last_closing_date is not None:
            entity_model.last_closing_date = last_closing_date
            entity_model.save(update_fields=["last_closing_date", "updated"])
        return entity_model

    def create_ledger(
        self,
        entity_model,
        *,
        name="API Ledger Locked Period Ledger",
        ledger_xid="api-ledger-locked-period-ledger",
    ):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=ledger_xid,
            entity=entity_model,
        )

    def make_timestamp(self, year, month, day):
        if settings.USE_TZ:
            return datetime(year, month, day, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(year, month, day, 12, 0)

    def create_posted_journal_entry(self, ledger_model, *, tx_date):
        return JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=self.make_timestamp(tx_date.year, tx_date.month, tx_date.day),
            description=f"API Posted Journal Entry {tx_date.isoformat()}",
            posted=True,
            force_create=True,
        )

    def test_current_includes_ledgers_with_no_posted_journal_entries(self):
        entity_model = self.create_entity(
            name="API Current No Activity Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-current-no-activity",
        )

        current_qs = LedgerModel.objects.for_entity(entity_model).current()

        self.assertTrue(current_qs.filter(uuid=ledger_model.uuid).exists())

    def test_current_includes_ledgers_with_posted_activity_after_last_closing_date(self):
        entity_model = self.create_entity(
            name="API Current After Closing Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-current-after-closing",
        )
        self.create_posted_journal_entry(
            ledger_model,
            tx_date=date(2026, 2, 1),
        )

        current_qs = LedgerModel.objects.for_entity(entity_model).current()

        self.assertTrue(current_qs.filter(uuid=ledger_model.uuid).exists())

    def test_current_excludes_ledgers_with_posted_activity_on_or_before_last_closing_date(self):
        entity_model = self.create_entity(
            name="API Current Closed Activity Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-current-closed-activity",
        )
        self.create_posted_journal_entry(
            ledger_model,
            tx_date=date(2026, 1, 31),
        )

        current_qs = LedgerModel.objects.for_entity(entity_model).current()

        self.assertFalse(current_qs.filter(uuid=ledger_model.uuid).exists())

    def test_current_includes_posted_activity_when_entity_has_no_closing_date(self):
        entity_model = self.create_entity(name="API Current No Closing Date Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-current-no-closing-date",
        )
        self.create_posted_journal_entry(
            ledger_model,
            tx_date=date(2026, 1, 31),
        )

        current_qs = LedgerModel.objects.for_entity(entity_model).current()

        self.assertTrue(current_qs.filter(uuid=ledger_model.uuid).exists())

    def test_has_jes_in_locked_period_returns_false_without_closing_date(self):
        entity_model = self.create_entity(name="API Locked Period No Closing Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-locked-period-no-closing",
        )
        self.create_posted_journal_entry(
            ledger_model,
            tx_date=date(2026, 1, 31),
        )

        self.assertFalse(ledger_model.has_jes_in_locked_period())

    def test_has_jes_in_locked_period_uses_annotated_earliest_posted_timestamp(self):
        entity_model = self.create_entity(
            name="API Locked Period Annotated Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-locked-period-annotated",
        )
        self.create_posted_journal_entry(
            ledger_model,
            tx_date=date(2026, 1, 15),
        )
        self.create_posted_journal_entry(
            ledger_model,
            tx_date=date(2026, 2, 15),
        )

        annotated_ledger = LedgerModel.objects.get(uuid=ledger_model.uuid)

        self.assertTrue(annotated_ledger.has_jes_in_locked_period())

    def test_has_jes_in_locked_period_force_evaluation_detects_any_posted_je_on_or_before_closing_date(self):
        entity_model = self.create_entity(
            name="API Locked Period Force Evaluation Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-locked-period-force-evaluation",
        )
        self.create_posted_journal_entry(
            ledger_model,
            tx_date=date(2026, 1, 15),
        )
        self.create_posted_journal_entry(
            ledger_model,
            tx_date=date(2026, 2, 15),
        )

        self.assertTrue(ledger_model.has_jes_in_locked_period())
