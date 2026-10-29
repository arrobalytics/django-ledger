"""
High-level API behavior tests for LedgerModel and JournalEntryModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldError
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel
from django_ledger.models.journal_entry import JournalEntryValidationError
from django_ledger.models.entity import EntityModel


class LedgerJournalEntryHighLevelAPITest(TestCase):
    """
    High-level behavior tests for LedgerModel and JournalEntryModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document small, deterministic accounting lifecycle invariants
    that should remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_ledger_contract_user",
            email="api-ledger-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Ledger Contract Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_entity_with_default_coa(self):
        entity_model = self.create_entity()
        entity_model.create_chart_of_accounts(
            coa_name="API Ledger Contract CoA",
            commit=True,
            assign_as_default=True,
        )
        entity_model.refresh_from_db()
        return entity_model

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_ledger(self, entity_model, *, posted=False, locked=False):
        return LedgerModel.objects.create(
            name="API Contract Ledger",
            ledger_xid="api-contract-ledger",
            entity=entity_model,
            posted=posted,
            locked=locked,
        )

    def create_journal_entry(
        self,
        ledger_model,
        *,
        posted=False,
        locked=False,
        description="API Contract Journal Entry",
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

    def test_ledger_is_created_under_entity_context(self):
        entity_model = self.create_entity_with_default_coa()

        ledger_model = self.create_ledger(entity_model)

        self.assertIsNotNone(ledger_model.uuid)
        self.assertEqual(ledger_model.entity_id, entity_model.uuid)
        self.assertEqual(ledger_model.name, "API Contract Ledger")
        self.assertFalse(ledger_model.posted)
        self.assertFalse(ledger_model.locked)

    def test_journal_entry_is_created_unposted_by_default(self):
        entity_model = self.create_entity_with_default_coa()
        ledger_model = self.create_ledger(entity_model)

        journal_entry = self.create_journal_entry(ledger_model)

        self.assertIsNotNone(journal_entry.uuid)
        self.assertEqual(journal_entry.ledger_id, ledger_model.uuid)
        self.assertFalse(journal_entry.posted)
        self.assertFalse(journal_entry.locked)
        self.assertFalse(journal_entry.is_locked())
        self.assertTrue(journal_entry.can_edit())
        self.assertTrue(journal_entry.can_delete())

    def test_journal_entry_cannot_be_created_posted_without_force_create(self):
        entity_model = self.create_entity_with_default_coa()
        ledger_model = self.create_ledger(entity_model)

        with self.assertRaises(FieldError):
            self.create_journal_entry(
                ledger_model,
                posted=True,
                locked=False,
            )

    def test_empty_journal_entry_is_not_marked_posted(self):
        entity_model = self.create_entity_with_default_coa()
        ledger_model = self.create_ledger(entity_model)
        journal_entry = self.create_journal_entry(ledger_model)

        result = journal_entry.mark_as_posted(commit=True)

        journal_entry.refresh_from_db()
        self.assertIsNone(result)
        self.assertFalse(journal_entry.posted)
        self.assertFalse(journal_entry.is_locked())

    def test_posted_journal_entry_is_considered_locked(self):
        entity_model = self.create_entity_with_default_coa()
        ledger_model = self.create_ledger(entity_model)
        journal_entry = self.create_journal_entry(
            ledger_model,
            posted=True,
            locked=False,
            force_create=True,
        )

        self.assertTrue(journal_entry.posted)
        self.assertFalse(journal_entry.locked)
        self.assertTrue(journal_entry.is_locked())
        self.assertFalse(journal_entry.can_edit())
        self.assertFalse(journal_entry.can_delete())

    def test_explicitly_locked_journal_entry_cannot_be_edited_or_deleted(self):
        entity_model = self.create_entity_with_default_coa()
        ledger_model = self.create_ledger(entity_model)
        journal_entry = self.create_journal_entry(
            ledger_model,
            posted=False,
            locked=True,
        )

        self.assertFalse(journal_entry.posted)
        self.assertTrue(journal_entry.locked)
        self.assertTrue(journal_entry.is_locked())
        self.assertFalse(journal_entry.can_edit())
        self.assertFalse(journal_entry.can_delete())

    def test_journal_entry_cannot_be_created_under_locked_ledger(self):
        entity_model = self.create_entity_with_default_coa()
        ledger_model = self.create_ledger(entity_model, locked=True)

        with self.assertRaises(JournalEntryValidationError):
            self.create_journal_entry(
                ledger_model,
                posted=False,
                locked=False,
            )

        self.assertTrue(ledger_model.locked)
