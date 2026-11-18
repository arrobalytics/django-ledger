"""
High-level API behavior tests for JournalEntryModel delete guards.

These tests cover public delete eligibility without exercising transaction,
posting, or signal behavior.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.journal_entry import JournalEntryValidationError


class JournalEntryDeleteAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_je_delete_admin",
            email="api-je-delete-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self, year=2026, month=1, day=15):
        if settings.USE_TZ:
            return datetime(year, month, day, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(year, month, day, 12, 0)

    def create_entity(
        self,
        *,
        name="API JE Delete Entity",
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

    def create_ledger(self, entity_model, *, name="API JE Delete Ledger"):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=f"{name.lower().replace(' ', '-')}-ledger",
            entity=entity_model,
        )

    def create_journal_entry(
        self,
        ledger_model,
        *,
        description="API JE Delete Journal Entry",
        timestamp=None,
        posted=False,
        locked=False,
        force_create=False,
    ):
        create_kwargs = {
            "ledger": ledger_model,
            "timestamp": timestamp if timestamp is not None else self.make_timestamp(),
            "description": description,
            "posted": posted,
            "locked": locked,
        }
        if force_create:
            create_kwargs["force_create"] = True
        return JournalEntryModel.objects.create(**create_kwargs)

    def assert_delete_is_rejected(self, journal_entry):
        journal_entry_uuid = journal_entry.uuid

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.delete()

        self.assertTrue(JournalEntryModel.objects.filter(uuid=journal_entry_uuid).exists())

    def test_unposted_unlocked_journal_entry_can_be_deleted(self):
        entity_model = self.create_entity(name="API JE Delete Allowed Entity")
        ledger_model = self.create_ledger(entity_model, name="API JE Delete Allowed Ledger")
        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Delete Allowed",
        )

        journal_entry_uuid = journal_entry.uuid
        journal_entry.delete()

        self.assertFalse(JournalEntryModel.objects.filter(uuid=journal_entry_uuid).exists())

    def test_posted_journal_entry_cannot_be_deleted(self):
        entity_model = self.create_entity(name="API JE Delete Posted Entity")
        ledger_model = self.create_ledger(entity_model, name="API JE Delete Posted Ledger")
        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Delete Posted",
            posted=True,
            force_create=True,
        )

        self.assert_delete_is_rejected(journal_entry)

    def test_explicitly_locked_journal_entry_cannot_be_deleted(self):
        entity_model = self.create_entity(name="API JE Delete Locked Entity")
        ledger_model = self.create_ledger(entity_model, name="API JE Delete Locked Ledger")
        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Delete Locked",
            locked=True,
        )

        self.assert_delete_is_rejected(journal_entry)

    def test_journal_entry_in_locked_period_cannot_be_deleted(self):
        entity_model = self.create_entity(
            name="API JE Delete Locked Period Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(entity_model, name="API JE Delete Locked Period Ledger")
        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Delete Locked Period",
            timestamp=self.make_timestamp(2026, 1, 15),
        )

        self.assert_delete_is_rejected(journal_entry)

    def test_delete_failure_leaves_journal_entry_in_database(self):
        entity_model = self.create_entity(name="API JE Delete Failure Entity")
        ledger_model = self.create_ledger(entity_model, name="API JE Delete Failure Ledger")
        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Delete Failure",
            posted=True,
            force_create=True,
        )
        journal_entry_uuid = journal_entry.uuid

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.delete()

        persisted_journal_entry = JournalEntryModel.objects.get(uuid=journal_entry_uuid)
        self.assertTrue(persisted_journal_entry.posted)
