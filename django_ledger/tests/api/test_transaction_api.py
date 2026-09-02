"""
High-level API behavior tests for TransactionModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from django_ledger.models import AccountModel, JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.journal_entry import JournalEntryValidationError
from django_ledger.models.transactions import TransactionModelValidationError


class TransactionHighLevelAPITest(TestCase):
    """
    High-level behavior tests for TransactionModel public API contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic double-entry invariants that should
    remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_transaction_contract_user",
            email="api-transaction-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_with_accounting_setup(self, *, name="API Transaction Contract Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Transaction Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        cash_account = coa_model.create_account(
            code="1010",
            name="API Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        expense_account = coa_model.create_account(
            code="6010",
            name="API Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
        )

        ledger_model = LedgerModel.objects.create(
            name="API Transaction Contract Ledger",
            ledger_xid="api-transaction-contract-ledger",
            entity=entity_model,
        )

        journal_entry = JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=self.make_timestamp(),
            description="API Transaction Contract Journal Entry",
        )

        return entity_model, coa_model, ledger_model, journal_entry, cash_account, expense_account

    def test_transaction_requires_journal_entry(self):
        _entity_model, _coa_model, _ledger_model, _journal_entry, cash_account, _expense_account = (
            self.create_entity_with_accounting_setup()
        )

        with self.assertRaises(TransactionModel.journal_entry.RelatedObjectDoesNotExist):
            with transaction.atomic():
                TransactionModel.objects.create(
                    tx_type=TransactionModel.DEBIT,
                    account=cash_account,
                    amount=Decimal("10.00"),
                    description="Orphan transaction should fail.",
                )

    def test_transaction_amount_cannot_be_negative(self):
        _entity_model, _coa_model, _ledger_model, journal_entry, cash_account, _expense_account = (
            self.create_entity_with_accounting_setup()
        )

        tx_model = TransactionModel(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=cash_account,
            amount=Decimal("-10.00"),
            description="Negative amount should fail validation.",
        )

        with self.assertRaises(ValidationError):
            tx_model.full_clean()

    def test_transaction_type_must_be_debit_or_credit(self):
        _entity_model, _coa_model, _ledger_model, journal_entry, cash_account, _expense_account = (
            self.create_entity_with_accounting_setup()
        )

        tx_model = TransactionModel(
            tx_type="invalid",
            journal_entry=journal_entry,
            account=cash_account,
            amount=Decimal("10.00"),
            description="Invalid tx_type should fail validation.",
        )

        with self.assertRaises(ValidationError):
            tx_model.full_clean()

    def test_root_account_cannot_receive_transaction(self):
        entity_model, _coa_model, _ledger_model, journal_entry, _cash_account, _expense_account = (
            self.create_entity_with_accounting_setup()
        )

        root_account = AccountModel.objects.for_entity(entity_model).is_coa_root().first()

        with self.assertRaises(ValidationError):
            with transaction.atomic():
                TransactionModel.objects.create(
                    tx_type=TransactionModel.DEBIT,
                    journal_entry=journal_entry,
                    account=root_account,
                    amount=Decimal("10.00"),
                    description="Root account should not receive transactions.",
                )

    def test_locked_journal_entry_rejects_new_transaction(self):
        _entity_model, _coa_model, _ledger_model, journal_entry, cash_account, _expense_account = (
            self.create_entity_with_accounting_setup()
        )

        journal_entry.locked = True
        journal_entry.save(update_fields=["locked"])

        with self.assertRaises(TransactionModelValidationError):
            with transaction.atomic():
                TransactionModel.objects.create(
                    tx_type=TransactionModel.DEBIT,
                    journal_entry=journal_entry,
                    account=cash_account,
                    amount=Decimal("10.00"),
                    description="Locked JE should reject transactions.",
                )

    def test_balanced_transactions_verify_successfully(self):
        _entity_model, _coa_model, _ledger_model, journal_entry, cash_account, expense_account = (
            self.create_entity_with_accounting_setup()
        )

        TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=expense_account,
            amount=Decimal("100.00"),
            description="Expense debit.",
        )

        TransactionModel.objects.create(
            tx_type=TransactionModel.CREDIT,
            journal_entry=journal_entry,
            account=cash_account,
            amount=Decimal("100.00"),
            description="Cash credit.",
        )

        journal_entry.verify()

    def test_imbalanced_transactions_fail_verification(self):
        _entity_model, _coa_model, _ledger_model, journal_entry, cash_account, expense_account = (
            self.create_entity_with_accounting_setup()
        )

        TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=expense_account,
            amount=Decimal("100.00"),
            description="Expense debit.",
        )

        TransactionModel.objects.create(
            tx_type=TransactionModel.CREDIT,
            journal_entry=journal_entry,
            account=cash_account,
            amount=Decimal("90.00"),
            description="Cash credit.",
        )

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.verify()

    def test_transactions_in_same_journal_entry_must_use_single_coa(self):
        _entity_model, _coa_model, _ledger_model, journal_entry, _cash_account, expense_account = (
            self.create_entity_with_accounting_setup()
        )

        other_entity_model = EntityModel.create_entity(
            name="API Other Entity",
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        other_coa_model = other_entity_model.create_chart_of_accounts(
            coa_name="API Other CoA",
            commit=True,
            assign_as_default=True,
        )

        other_cash_account = other_coa_model.create_account(
            code="1010",
            name="API Other Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=expense_account,
            amount=Decimal("100.00"),
            description="Expense debit.",
        )

        TransactionModel.objects.create(
            tx_type=TransactionModel.CREDIT,
            journal_entry=journal_entry,
            account=other_cash_account,
            amount=Decimal("100.00"),
            description="Other entity cash credit.",
        )

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.verify()
