"""
High-level API behavior tests for Django Ledger IO engine.

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
from django.test import TestCase

from django_ledger.io.io_library import IOLibrary, IOBluePrint, IOCursorValidationError
from django_ledger.models import AccountModel, JournalEntryModel, TransactionModel
from django_ledger.models.entity import EntityModel


class IOHighLevelAPITest(TestCase):
    """
    High-level behavior tests for Django Ledger IO engine contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic posting-engine behavior that should
    remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_io_contract_user",
            email="api-io-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_with_accounting_setup(self, *, name="API IO Contract Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API IO Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        cash_account = coa_model.create_account(
            code="1010",
            name="API IO Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

        expense_account = coa_model.create_account(
            code="6010",
            name="API IO Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
        )

        return entity_model, coa_model, cash_account, expense_account

    def create_balanced_blueprint(self, *, cash_account, expense_account):
        blueprint = IOBluePrint(name="api-io-expense-blueprint")

        blueprint.debit(
            account_code=expense_account.code,
            amount=Decimal("100.00"),
            description="API IO expense debit.",
        )

        blueprint.credit(
            account_code=cash_account.code,
            amount=Decimal("100.00"),
            description="API IO cash credit.",
        )

        return blueprint

    def first_commit_payload(self, commit_result):
        self.assertEqual(
            len(commit_result),
            1,
            "A single-blueprint commit without an explicit ledger should produce one ledger payload.",
        )

        return next(iter(commit_result.values()))

    def test_io_blueprint_accepts_balanced_debit_credit_instructions(self):
        _entity_model, _coa_model, cash_account, expense_account = (
            self.create_entity_with_accounting_setup()
        )

        blueprint = self.create_balanced_blueprint(
            cash_account=cash_account,
            expense_account=expense_account,
        )

        self.assertEqual(blueprint.name, "api-io-expense-blueprint")
        self.assertEqual(len(blueprint.registry), 2)

    def test_io_library_registers_blueprint_factory_by_function_name(self):
        def expense_blueprint():
            return IOBluePrint(name="api-io-expense-blueprint")

        io_library = IOLibrary(name="api-io-library")
        io_library.register(expense_blueprint)

        self.assertIs(io_library.get_blueprint("expense_blueprint"), expense_blueprint)

    def test_io_blueprint_commit_creates_balanced_journal_entry(self):
        entity_model, _coa_model, cash_account, expense_account = (
            self.create_entity_with_accounting_setup()
        )

        blueprint = self.create_balanced_blueprint(
            cash_account=cash_account,
            expense_account=expense_account,
        )

        result = blueprint.commit(
            entity_model=entity_model,
            user_model=self.user,
            je_timestamp=self.make_timestamp(),
            post_new_ledgers=False,
            post_journal_entries=False,
        )

        payload = self.first_commit_payload(result)

        self.assertIn("ledger_model", payload)
        self.assertIn("journal_entry", payload)
        self.assertIn("txs_models", payload)

        journal_entry = payload["journal_entry"]
        transactions = payload["txs_models"]

        self.assertIsInstance(journal_entry, JournalEntryModel)
        self.assertEqual(journal_entry.ledger.entity_id, entity_model.uuid)
        self.assertFalse(journal_entry.posted)
        self.assertEqual(len(transactions), 2)

        debit_total = sum(
            tx.amount for tx in transactions if tx.tx_type == TransactionModel.DEBIT
        )
        credit_total = sum(
            tx.amount for tx in transactions if tx.tx_type == TransactionModel.CREDIT
        )

        self.assertEqual(debit_total, Decimal("100.00"))
        self.assertEqual(credit_total, Decimal("100.00"))
        self.assertEqual(debit_total, credit_total)

        self.assertTrue(
            TransactionModel.objects.filter(
                journal_entry=journal_entry,
                tx_type=TransactionModel.DEBIT,
                account=expense_account,
                amount=Decimal("100.00"),
            ).exists()
        )

        self.assertTrue(
            TransactionModel.objects.filter(
                journal_entry=journal_entry,
                tx_type=TransactionModel.CREDIT,
                account=cash_account,
                amount=Decimal("100.00"),
            ).exists()
        )

    def test_io_blueprint_commit_keeps_transactions_within_entity_default_coa(self):
        entity_model, coa_model, cash_account, expense_account = (
            self.create_entity_with_accounting_setup()
        )

        blueprint = self.create_balanced_blueprint(
            cash_account=cash_account,
            expense_account=expense_account,
        )

        result = blueprint.commit(
            entity_model=entity_model,
            user_model=self.user,
            je_timestamp=self.make_timestamp(),
            post_new_ledgers=False,
            post_journal_entries=False,
        )

        payload = self.first_commit_payload(result)
        journal_entry = payload["journal_entry"]

        tx_accounts = AccountModel.objects.filter(
            transactionmodel__journal_entry=journal_entry,
        )

        self.assertEqual(tx_accounts.count(), 2)
        self.assertTrue(tx_accounts.filter(uuid=cash_account.uuid).exists())
        self.assertTrue(tx_accounts.filter(uuid=expense_account.uuid).exists())

        for account in tx_accounts:
            self.assertEqual(account.coa_model_id, coa_model.uuid)
            self.assertFalse(account.is_root_account())
            self.assertTrue(account.active)

    def test_imbalanced_io_blueprint_commit_fails(self):
        entity_model, _coa_model, cash_account, expense_account = (
            self.create_entity_with_accounting_setup()
        )

        blueprint = IOBluePrint(name="api-io-imbalanced-blueprint")
        blueprint.debit(
            account_code=expense_account.code,
            amount=Decimal("100.00"),
            description="API IO expense debit.",
        )
        blueprint.credit(
            account_code=cash_account.code,
            amount=Decimal("90.00"),
            description="API IO cash credit.",
        )

        with self.assertRaises(IOCursorValidationError):
            blueprint.commit(
                entity_model=entity_model,
                user_model=self.user,
                je_timestamp=self.make_timestamp(),
                post_new_ledgers=False,
                post_journal_entries=False,
            )
