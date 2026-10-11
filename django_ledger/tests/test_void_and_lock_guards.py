from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from django_ledger.models import BillModel, InvoiceModel, JournalEntryModel
from django_ledger.models.journal_entry import JournalEntryValidationError
from django_ledger.tests.base import DjangoLedgerBaseTest


class CanVoidTests(SimpleTestCase):
    def test_void_requires_no_payment(self):
        for model in (BillModel, InvoiceModel):
            for amount_paid, expected in ((Decimal(0), True), (Decimal('0.00'), True), (Decimal('0.01'), False)):
                with (
                    self.subTest(model=model.__name__, amount_paid=amount_paid),
                    patch.object(model, 'is_approved', return_value=True),
                ):
                    self.assertIs(model(amount_paid=amount_paid).can_void(), expected)

    def test_void_requires_approval(self):
        for model in (BillModel, InvoiceModel):
            with self.subTest(model=model.__name__), patch.object(model, 'is_approved', return_value=False):
                self.assertIs(model(amount_paid=Decimal(0)).can_void(), False)


class MarkAsLockedGuardTests(DjangoLedgerBaseTest):
    def test_lock_refusal_depends_on_raise_exception(self):
        entity_model = self.get_random_entity_model()
        ledger_model = self.get_random_ledger(entity_model=entity_model)
        je_model: JournalEntryModel = self.get_random_je(entity_model=entity_model, ledger_model=ledger_model)
        je_model.mark_as_locked(commit=True)
        self.assertTrue(je_model.is_locked())

        with self.assertRaises(JournalEntryValidationError):
            je_model.mark_as_locked(raise_exception=True)
        je_model.mark_as_locked(raise_exception=False)
        self.assertTrue(je_model.is_locked())

    def test_locking_a_locked_ledger_still_locks_its_entries(self):
        # LedgerModel.lock_journal_entries relies on mark_as_locked(raise_exception=False)
        # locking entries even though can_lock() is False once the ledger is locked.
        entity_model = self.get_random_entity_model()
        ledger_model = next(
            ledger
            for ledger in entity_model.get_ledgers(posted=True)
            if ledger.can_lock() and ledger.journal_entries.exists()
        )
        ledger_model.journal_entries.update(locked=False)
        ledger_model.lock(commit=True)
        je_model = ledger_model.journal_entries.first()
        self.assertFalse(je_model.can_lock())

        with self.assertRaises(JournalEntryValidationError):
            je_model.mark_as_locked(raise_exception=True)
        je_model.mark_as_locked(raise_exception=False)
        self.assertTrue(je_model.is_locked())
