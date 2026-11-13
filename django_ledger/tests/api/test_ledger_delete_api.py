"""
High-level API behavior tests for LedgerModel delete guards.

These tests cover public delete eligibility without exercising wrapper model
lifecycles or signals.
"""

from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.ledger import LedgerModelValidationError


class LedgerDeleteAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_ledger_delete_admin",
            email="api-ledger-delete-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(
        self,
        *,
        name="API Ledger Delete Entity",
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
        name="API Ledger Delete Ledger",
        ledger_xid="api-ledger-delete-ledger",
        posted=False,
        locked=False,
        additional_info=None,
    ):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=ledger_xid,
            entity=entity_model,
            posted=posted,
            locked=locked,
            additional_info={} if additional_info is None else additional_info,
        )

    def make_timestamp(self, year, month, day):
        if settings.USE_TZ:
            return datetime(year, month, day, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(year, month, day, 12, 0)

    def create_posted_journal_entry(self, ledger_model, *, tx_date):
        return JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=self.make_timestamp(tx_date.year, tx_date.month, tx_date.day),
            description=f"API Delete Posted Journal Entry {tx_date.isoformat()}",
            posted=True,
            force_create=True,
        )

    def assert_delete_is_rejected(self, ledger_model):
        self.assertFalse(ledger_model.can_delete())

        with self.assertRaises(LedgerModelValidationError):
            ledger_model.delete()

        self.assertTrue(LedgerModel.objects.filter(uuid=ledger_model.uuid).exists())

    def test_unposted_unlocked_non_wrapped_ledger_without_locked_period_journal_entries_can_delete(self):
        entity_model = self.create_entity(name="API Ledger Delete Allowed Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-delete-allowed",
            posted=False,
            locked=False,
        )

        self.assertTrue(ledger_model.can_delete())

        ledger_uuid = ledger_model.uuid
        ledger_model.delete()

        self.assertFalse(LedgerModel.objects.filter(uuid=ledger_uuid).exists())

    def test_posted_ledger_cannot_delete(self):
        entity_model = self.create_entity(name="API Ledger Delete Posted Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-delete-posted",
            posted=True,
            locked=False,
        )

        self.assert_delete_is_rejected(ledger_model)

    def test_locked_ledger_cannot_delete(self):
        entity_model = self.create_entity(name="API Ledger Delete Locked Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-delete-locked",
            posted=False,
            locked=True,
        )

        self.assert_delete_is_rejected(ledger_model)

    def test_wrapped_ledger_metadata_prevents_delete(self):
        entity_model = self.create_entity(name="API Ledger Delete Wrapped Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-delete-wrapped",
            posted=False,
            locked=False,
            additional_info={
                "wrapped_model": {
                    "model": "billmodel",
                    "uuid": uuid4(),
                }
            },
        )

        self.assert_delete_is_rejected(ledger_model)

    def test_ledger_with_posted_journal_entry_in_locked_period_cannot_delete(self):
        entity_model = self.create_entity(
            name="API Ledger Delete Locked Period Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-delete-locked-period",
            posted=False,
            locked=False,
        )
        self.create_posted_journal_entry(
            ledger_model,
            tx_date=date(2026, 1, 15),
        )

        self.assert_delete_is_rejected(ledger_model)
