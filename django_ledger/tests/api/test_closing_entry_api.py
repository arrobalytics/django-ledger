"""
High-level API behavior tests for ClosingEntryModel and ClosingEntryTransactionModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from django_ledger.models import JournalEntryModel, TransactionModel
from django_ledger.models.closing_entry import (
    ClosingEntryModel,
    ClosingEntryTransactionModel,
    ClosingEntryValidationError,
)
from django_ledger.models.entity import EntityModel


class ClosingEntryHighLevelAPITest(TestCase):
    """
    High-level behavior tests for ClosingEntryModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic closing-entry invariants that should
    remain true across swappable-model refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_closing_entry_contract_user",
            email="api-closing-entry-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Closing Entry Contract Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )

        cash_account = coa_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        equity_account = coa_model.create_account(
            code="3010",
            name=f"{name} Equity Account",
            role="eq_capital",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "equity_account": equity_account,
        }

    def create_closing_entry(self, setup, *, closing_date=date(2025, 12, 31)):
        closing_entry = ClosingEntryModel.objects.create(
            entity_model=setup["entity_model"],
            closing_date=closing_date,
        )

        closing_entry.refresh_from_db()
        return closing_entry

    def create_balanced_closing_entry_transactions(self, closing_entry, setup):
        debit_tx = ClosingEntryTransactionModel.objects.create(
            closing_entry_model=closing_entry,
            account_model=setup["cash_account"],
            tx_type=TransactionModel.DEBIT,
            balance=Decimal("100.00"),
        )

        credit_tx = ClosingEntryTransactionModel.objects.create(
            closing_entry_model=closing_entry,
            account_model=setup["equity_account"],
            tx_type=TransactionModel.CREDIT,
            balance=Decimal("100.00"),
        )

        return debit_tx, credit_tx

    def test_closing_entry_creation_creates_hidden_posted_ledger(self):
        setup = self.create_entity_setup()

        closing_entry = self.create_closing_entry(setup)

        self.assertIsInstance(closing_entry, ClosingEntryModel)
        self.assertIsNotNone(closing_entry.uuid)
        self.assertEqual(closing_entry.entity_model_id, setup["entity_model"].uuid)
        self.assertEqual(closing_entry.closing_date, date(2025, 12, 31))
        self.assertFalse(closing_entry.is_posted())
        self.assertFalse(closing_entry.posted)

        self.assertIsNotNone(closing_entry.ledger_model_id)
        self.assertEqual(closing_entry.ledger_model.entity_id, setup["entity_model"].uuid)
        self.assertTrue(closing_entry.ledger_model.hidden)
        self.assertTrue(closing_entry.ledger_model.posted)
        self.assertFalse(closing_entry.ledger_model.locked)

    def test_closing_entry_for_entity_limits_queryset_to_entity_scope(self):
        setup = self.create_entity_setup(name="API Closing Entry Entity A")
        other_setup = self.create_entity_setup(name="API Closing Entry Entity B")

        closing_entry = self.create_closing_entry(setup)
        other_closing_entry = self.create_closing_entry(other_setup)

        scoped_qs = ClosingEntryModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(scoped_qs.filter(uuid=closing_entry.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_closing_entry.uuid).exists())

    def test_closing_entry_posted_and_not_posted_queryset_contracts(self):
        setup = self.create_entity_setup()

        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_entry_transactions(closing_entry, setup)

        closing_entries_qs = ClosingEntryModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(closing_entries_qs.not_posted().filter(uuid=closing_entry.uuid).exists())
        self.assertFalse(closing_entries_qs.posted().filter(uuid=closing_entry.uuid).exists())

        closing_entry.mark_as_posted(
            commit=True,
            update_entity_meta=False,
        )
        closing_entry.refresh_from_db()

        self.assertTrue(closing_entries_qs.posted().filter(uuid=closing_entry.uuid).exists())
        self.assertFalse(closing_entries_qs.not_posted().filter(uuid=closing_entry.uuid).exists())

    def test_closing_entry_date_is_unique_per_entity(self):
        setup = self.create_entity_setup()

        self.create_closing_entry(setup, closing_date=date(2025, 12, 31))

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_closing_entry(setup, closing_date=date(2025, 12, 31))

    def test_balanced_closing_entry_can_be_posted_and_creates_locked_journal_entry(self):
        setup = self.create_entity_setup()

        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_entry_transactions(closing_entry, setup)

        closing_entry.mark_as_posted(
            commit=True,
            update_entity_meta=False,
        )
        closing_entry.refresh_from_db()

        self.assertTrue(closing_entry.is_posted())
        self.assertFalse(closing_entry.can_post())
        self.assertTrue(closing_entry.can_unpost())
        self.assertFalse(closing_entry.can_update_txs())
        self.assertFalse(closing_entry.can_delete())

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

        txs = TransactionModel.objects.filter(journal_entry=journal_entry)

        self.assertEqual(txs.count(), 2)
        self.assertEqual(
            sum(tx.amount for tx in txs if tx.tx_type == TransactionModel.DEBIT),
            Decimal("100.00"),
        )
        self.assertEqual(
            sum(tx.amount for tx in txs if tx.tx_type == TransactionModel.CREDIT),
            Decimal("100.00"),
        )

        closing_entry.ledger_model.refresh_from_db()
        self.assertTrue(closing_entry.ledger_model.locked)

    def test_imbalanced_closing_entry_cannot_be_posted(self):
        setup = self.create_entity_setup()

        closing_entry = self.create_closing_entry(setup)

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
            balance=Decimal("90.00"),
        )

        with self.assertRaises(ClosingEntryValidationError):
            closing_entry.mark_as_posted(
                commit=True,
                update_entity_meta=False,
            )

        closing_entry.refresh_from_db()
        self.assertFalse(closing_entry.is_posted())

    def test_posted_closing_entry_can_be_unposted_and_removes_generated_entries(self):
        setup = self.create_entity_setup()

        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_entry_transactions(closing_entry, setup)

        closing_entry.mark_as_posted(
            commit=True,
            update_entity_meta=False,
        )
        closing_entry.refresh_from_db()

        self.assertTrue(
            JournalEntryModel.objects.filter(
                ledger=closing_entry.ledger_model,
                is_closing_entry=True,
            ).exists()
        )

        closing_entry.mark_as_unposted(
            commit=True,
            update_entity_meta=False,
        )
        closing_entry.refresh_from_db()

        self.assertFalse(closing_entry.is_posted())
        self.assertTrue(closing_entry.can_post())
        self.assertTrue(closing_entry.can_update_txs())
        self.assertTrue(closing_entry.can_delete())

        self.assertFalse(
            JournalEntryModel.objects.filter(
                ledger=closing_entry.ledger_model,
                is_closing_entry=True,
            ).exists()
        )

        self.assertFalse(
            TransactionModel.objects.filter(
                journal_entry__ledger=closing_entry.ledger_model,
            ).exists()
        )

        closing_entry.ledger_model.refresh_from_db()
        self.assertFalse(closing_entry.ledger_model.locked)

    def test_posted_closing_entry_cannot_be_deleted(self):
        setup = self.create_entity_setup()

        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_entry_transactions(closing_entry, setup)

        closing_entry.mark_as_posted(
            commit=True,
            update_entity_meta=False,
        )
        closing_entry.refresh_from_db()

        with self.assertRaises(ClosingEntryValidationError):
            closing_entry.delete()

    def test_closing_entry_transaction_for_closing_date_queryset_contract(self):
        setup = self.create_entity_setup()
        other_setup = self.create_entity_setup(name="API Other Closing Entry Entity")

        closing_entry = self.create_closing_entry(setup, closing_date=date(2025, 12, 31))
        other_closing_entry = self.create_closing_entry(other_setup, closing_date=date(2025, 12, 31))

        debit_tx, _credit_tx = self.create_balanced_closing_entry_transactions(closing_entry, setup)
        other_debit_tx, _other_credit_tx = self.create_balanced_closing_entry_transactions(
            other_closing_entry,
            other_setup,
        )

        closing_date_qs = ClosingEntryTransactionModel.objects.for_closing_date(
            date(2025, 12, 31),
        )

        self.assertTrue(closing_date_qs.filter(uuid=debit_tx.uuid).exists())
        self.assertTrue(closing_date_qs.filter(uuid=other_debit_tx.uuid).exists())

    def test_closing_entry_transaction_for_entity_currently_exposes_lazy_loader_bug(self):
        setup = self.create_entity_setup()
        closing_entry = self.create_closing_entry(setup, closing_date=date(2025, 12, 31))
        self.create_balanced_closing_entry_transactions(closing_entry, setup)

        with self.assertRaises(AttributeError):
            ClosingEntryTransactionModel.objects.for_entity(setup["entity_model"])

    def test_closing_entry_transaction_negative_balance_flips_tx_type_and_abs_balance(self):
        setup = self.create_entity_setup()
        closing_entry = self.create_closing_entry(setup)

        ce_tx = ClosingEntryTransactionModel.objects.create(
            closing_entry_model=closing_entry,
            account_model=setup["cash_account"],
            tx_type=TransactionModel.DEBIT,
            balance=Decimal("-25.00"),
        )

        ce_tx.refresh_from_db()

        self.assertTrue(ce_tx.is_credit())
        self.assertFalse(ce_tx.is_debit())
        self.assertEqual(ce_tx.balance, Decimal("25.000000"))
