"""
High-level API behavior tests for JournalEntryModel numbering and pre-save.

These tests cover journal-entry number generation, fiscal-year sequencing, and
the locked-ledger creation guard.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.journal_entry import JournalEntryValidationError
from django_ledger.settings import (
    DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING,
    DJANGO_LEDGER_JE_NUMBER_NO_UNIT_PREFIX,
    DJANGO_LEDGER_JE_NUMBER_PREFIX,
)


class JournalEntryNumberingAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_je_numbering_admin",
            email="api-je-numbering-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self, year=2026, month=1, day=15):
        if settings.USE_TZ:
            return datetime(year, month, day, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(year, month, day, 12, 0)

    def create_entity(self, *, name="API JE Numbering Entity", fy_start_month=1):
        return EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=fy_start_month,
        )

    def create_ledger(
        self,
        entity_model,
        *,
        name="API JE Numbering Ledger",
        locked=False,
    ):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=f"{name.lower().replace(' ', '-')}-ledger",
            entity=entity_model,
            locked=locked,
        )

    def create_journal_entry(
        self,
        ledger_model,
        *,
        description="API JE Numbering Journal Entry",
        timestamp=None,
    ):
        return JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=timestamp if timestamp is not None else self.make_timestamp(),
            description=description,
        )

    def assert_je_number(self, number, *, fiscal_year, sequence):
        self.assertTrue(number)
        self.assertTrue(number.startswith(f"{DJANGO_LEDGER_JE_NUMBER_PREFIX}-"))
        self.assertIn(f"-{fiscal_year}-", number)
        self.assertIn(f"-{DJANGO_LEDGER_JE_NUMBER_NO_UNIT_PREFIX}-", number)
        self.assertTrue(
            number.endswith(str(sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING))
        )

    def clear_je_number(self, journal_entry):
        JournalEntryModel.objects.filter(uuid=journal_entry.uuid).update(je_number="")
        journal_entry.refresh_from_db()

    def test_can_generate_je_number_is_true_with_ledger_and_no_number(self):
        entity_model = self.create_entity(name="API JE Can Generate Entity")
        ledger_model = self.create_ledger(entity_model)
        unsaved_journal_entry = JournalEntryModel(
            ledger=ledger_model,
            timestamp=self.make_timestamp(),
            description="API JE Unsaved Can Generate",
        )
        saved_journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Saved Can Generate",
        )
        self.clear_je_number(saved_journal_entry)

        self.assertTrue(unsaved_journal_entry.can_generate_je_number())
        self.assertTrue(saved_journal_entry.can_generate_je_number())

    def test_generate_je_number_commit_false_assigns_number_in_memory_without_saving_entry(self):
        entity_model = self.create_entity(name="API JE Generate Commit False Entity")
        ledger_model = self.create_ledger(entity_model)
        journal_entry = JournalEntryModel(
            ledger=ledger_model,
            timestamp=self.make_timestamp(),
            description="API JE Generate Commit False",
        )

        number = journal_entry.generate_je_number(commit=False)

        self.assertEqual(number, journal_entry.je_number)
        self.assert_je_number(number, fiscal_year=2026, sequence=1)
        self.assertFalse(JournalEntryModel.objects.filter(uuid=journal_entry.uuid).exists())

    def test_generate_je_number_commit_true_persists_generated_number(self):
        entity_model = self.create_entity(name="API JE Generate Commit True Entity")
        ledger_model = self.create_ledger(entity_model)
        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Generate Commit True",
        )
        self.clear_je_number(journal_entry)

        number = journal_entry.generate_je_number(commit=True)

        journal_entry.refresh_from_db()
        self.assertEqual(number, journal_entry.je_number)
        self.assert_je_number(number, fiscal_year=2026, sequence=2)

    def test_je_number_is_automatically_generated_on_create(self):
        entity_model = self.create_entity(name="API JE Pre Save Number Entity")
        ledger_model = self.create_ledger(entity_model)

        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Pre Save Number",
        )

        self.assert_je_number(journal_entry.je_number, fiscal_year=2026, sequence=1)
        self.assertFalse(journal_entry.can_generate_je_number())

    def test_sequential_je_numbers_advance_within_entity_fiscal_year_and_no_unit_scope(self):
        entity_model = self.create_entity(name="API JE Sequential Entity")
        ledger_model = self.create_ledger(entity_model)

        first_journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Sequential First",
        )
        second_journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Sequential Second",
        )

        self.assertNotEqual(first_journal_entry.je_number, second_journal_entry.je_number)
        self.assert_je_number(first_journal_entry.je_number, fiscal_year=2026, sequence=1)
        self.assert_je_number(second_journal_entry.je_number, fiscal_year=2026, sequence=2)

    def test_je_numbering_uses_separate_sequences_across_fiscal_years(self):
        entity_model = self.create_entity(name="API JE Fiscal Year Sequence Entity")
        ledger_model = self.create_ledger(entity_model)

        fy_2026_journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE FY 2026",
            timestamp=self.make_timestamp(2026, 12, 31),
        )
        fy_2027_journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE FY 2027",
            timestamp=self.make_timestamp(2027, 1, 1),
        )

        self.assert_je_number(fy_2026_journal_entry.je_number, fiscal_year=2026, sequence=1)
        self.assert_je_number(fy_2027_journal_entry.je_number, fiscal_year=2027, sequence=1)

    def test_creating_journal_entry_under_locked_ledger_raises_validation_error(self):
        entity_model = self.create_entity(name="API JE Locked Ledger Guard Entity")
        ledger_model = self.create_ledger(
            entity_model,
            name="API JE Locked Ledger Guard",
            locked=True,
        )

        with self.assertRaises(JournalEntryValidationError):
            self.create_journal_entry(
                ledger_model,
                description="API JE Locked Ledger Rejected",
            )

        self.assertFalse(JournalEntryModel.objects.filter(ledger=ledger_model).exists())
