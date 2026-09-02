"""
High-level API behavior tests for JournalEntryModel locked-period predicates.

These tests cover public state and capability checks without exercising
lifecycle transitions or signals.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel
from django_ledger.models.entity import EntityModel


class JournalEntryLockedPeriodAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_je_locked_period_admin",
            email="api-je-locked-period-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self, year=2026, month=1, day=15):
        if settings.USE_TZ:
            return datetime(year, month, day, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(year, month, day, 12, 0)

    def create_entity(
        self,
        *,
        name="API JE Locked Period Entity",
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

    def create_ledger(self, entity_model, *, name="API JE Locked Period Ledger"):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=f"{name.lower().replace(' ', '-')}-ledger",
            entity=entity_model,
        )

    def create_journal_entry(
        self,
        ledger_model,
        *,
        description="API JE Locked Period Journal Entry",
        timestamp=None,
        posted=False,
        locked=False,
        force_create=False,
    ):
        create_kwargs = {
            "ledger": ledger_model,
            "timestamp": timestamp or self.make_timestamp(),
            "description": description,
            "posted": posted,
            "locked": locked,
        }
        if force_create:
            create_kwargs["force_create"] = True
        return JournalEntryModel.objects.create(**create_kwargs)

    def test_is_in_locked_period_is_false_without_entity_last_closing_date(self):
        entity_model = self.create_entity(
            name="API JE No Closing Date Entity",
        )
        ledger_model = self.create_ledger(entity_model)
        journal_entry = self.create_journal_entry(
            ledger_model,
            timestamp=self.make_timestamp(2026, 1, 15),
        )

        self.assertFalse(journal_entry.is_in_locked_period())

    def test_is_in_locked_period_is_true_on_or_before_last_closing_date(self):
        entity_model = self.create_entity(
            name="API JE Closing Date Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(entity_model)
        before_closing = self.create_journal_entry(
            ledger_model,
            description="API JE Before Closing",
            timestamp=self.make_timestamp(2026, 1, 15),
        )
        on_closing = self.create_journal_entry(
            ledger_model,
            description="API JE On Closing",
            timestamp=self.make_timestamp(2026, 1, 31),
        )
        after_closing = self.create_journal_entry(
            ledger_model,
            description="API JE After Closing",
            timestamp=self.make_timestamp(2026, 2, 1),
        )

        self.assertTrue(before_closing.is_in_locked_period())
        self.assertTrue(on_closing.is_in_locked_period())
        self.assertFalse(after_closing.is_in_locked_period())

    def test_is_in_locked_period_accepts_date_and_datetime_override(self):
        entity_model = self.create_entity(
            name="API JE Closing Date Override Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(entity_model)
        journal_entry = self.create_journal_entry(
            ledger_model,
            timestamp=self.make_timestamp(2026, 2, 15),
        )

        self.assertTrue(journal_entry.is_in_locked_period(new_timestamp=date(2026, 1, 31)))
        self.assertTrue(journal_entry.is_in_locked_period(new_timestamp=self.make_timestamp(2026, 1, 31)))
        self.assertFalse(journal_entry.is_in_locked_period(new_timestamp=date(2026, 2, 1)))
        self.assertFalse(journal_entry.is_in_locked_period(new_timestamp=self.make_timestamp(2026, 2, 1)))

    def test_is_locked_reflects_posted_explicit_ledger_and_period_locks(self):
        current_entity = self.create_entity(
            name="API JE Is Locked Current Entity",
        )
        current_ledger = self.create_ledger(current_entity)

        posted_journal_entry = self.create_journal_entry(
            current_ledger,
            description="API JE Posted Lock",
            posted=True,
            force_create=True,
        )
        explicit_locked_journal_entry = self.create_journal_entry(
            current_ledger,
            description="API JE Explicit Lock",
            locked=True,
        )
        ledger_locked_journal_entry = self.create_journal_entry(
            current_ledger,
            description="API JE Ledger Lock",
        )
        current_ledger.locked = True
        current_ledger.save(update_fields=["locked", "updated"])

        locked_period_entity = self.create_entity(
            name="API JE Is Locked Period Entity",
            last_closing_date=date(2026, 1, 31),
        )
        locked_period_ledger = self.create_ledger(locked_period_entity)
        locked_period_journal_entry = self.create_journal_entry(
            locked_period_ledger,
            description="API JE Locked Period Lock",
            timestamp=self.make_timestamp(2026, 1, 15),
        )

        self.assertTrue(posted_journal_entry.is_locked())
        self.assertTrue(explicit_locked_journal_entry.is_locked())
        self.assertTrue(ledger_locked_journal_entry.is_locked())
        self.assertTrue(ledger_locked_journal_entry.ledger_is_locked())
        self.assertTrue(locked_period_journal_entry.is_locked())

    def test_capability_predicates_reflect_locked_period_restrictions(self):
        entity_model = self.create_entity(
            name="API JE Locked Period Capability Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(entity_model)
        locked_unposted = self.create_journal_entry(
            ledger_model,
            description="API JE Locked Period Unposted",
            timestamp=self.make_timestamp(2026, 1, 15),
            locked=True,
        )
        posted = self.create_journal_entry(
            ledger_model,
            description="API JE Locked Period Posted",
            timestamp=self.make_timestamp(2026, 1, 15),
            posted=True,
            force_create=True,
        )

        self.assertFalse(locked_unposted.can_post())
        self.assertFalse(posted.can_unpost())
        self.assertFalse(locked_unposted.can_lock())
        self.assertFalse(locked_unposted.can_unlock())
        self.assertFalse(locked_unposted.can_delete())
        self.assertFalse(locked_unposted.can_edit())

    def test_capability_predicates_reflect_ledger_lock_restrictions(self):
        entity_model = self.create_entity(
            name="API JE Ledger Lock Capability Entity",
        )
        ledger_model = self.create_ledger(entity_model)
        unposted = self.create_journal_entry(
            ledger_model,
            description="API JE Ledger Lock Unposted",
        )
        locked_unposted = self.create_journal_entry(
            ledger_model,
            description="API JE Ledger Lock Explicitly Locked",
            locked=True,
        )
        posted = self.create_journal_entry(
            ledger_model,
            description="API JE Ledger Lock Posted",
            posted=True,
            force_create=True,
        )

        ledger_model.locked = True
        ledger_model.save(update_fields=["locked", "updated"])

        self.assertFalse(locked_unposted.can_post())
        self.assertFalse(posted.can_unpost())
        self.assertFalse(unposted.can_lock())
        self.assertFalse(locked_unposted.can_unlock())
        self.assertFalse(unposted.can_delete())
        self.assertFalse(unposted.can_edit())

    def test_capability_predicates_allow_current_unlocked_unposted_entries(self):
        entity_model = self.create_entity(
            name="API JE Current Capability Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(entity_model)
        journal_entry = self.create_journal_entry(
            ledger_model,
            timestamp=self.make_timestamp(2026, 2, 15),
        )

        self.assertTrue(journal_entry.can_lock())
        self.assertTrue(journal_entry.can_delete())
        self.assertTrue(journal_entry.can_edit())

        journal_entry.locked = True
        self.assertTrue(journal_entry.can_post())
        self.assertTrue(journal_entry.can_unlock())
