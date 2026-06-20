"""
High-level API behavior tests for JournalEntryModel transaction validation.

These tests cover transaction queryset, balance, and chart-of-accounts
validation without exercising save, clean, or posting behavior.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.journal_entry import JournalEntryValidationError


class JournalEntryValidationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_je_validation_admin",
            email="api-je-validation-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_with_accounting_setup(self, *, name="API JE Validation Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
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
            name=f"{name} Cash",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense",
            role="ex_regular",
            balance_type="debit",
            active=True,
        )
        ledger_model = LedgerModel.objects.create(
            name=f"{name} Ledger",
            ledger_xid=f"{name.lower().replace(' ', '-')}-ledger",
            entity=entity_model,
        )
        journal_entry = JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=self.make_timestamp(),
            description=f"{name} Journal Entry",
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "expense_account": expense_account,
            "ledger_model": ledger_model,
            "journal_entry": journal_entry,
        }

    def create_journal_entry(self, ledger_model, *, description):
        return JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=self.make_timestamp(),
            description=description,
        )

    def add_transactions(
        self,
        journal_entry,
        *,
        debit_account,
        credit_account,
        debit_amount=Decimal("100.00"),
        credit_amount=Decimal("100.00"),
    ):
        debit_tx = TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=debit_account,
            amount=debit_amount,
            description="Validation debit.",
        )
        credit_tx = TransactionModel.objects.create(
            tx_type=TransactionModel.CREDIT,
            journal_entry=journal_entry,
            account=credit_account,
            amount=credit_amount,
            description="Validation credit.",
        )
        return debit_tx, credit_tx

    def test_get_transaction_queryset_returns_this_entries_transactions_with_or_without_accounts(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Validation QuerySet Entity",
        )
        journal_entry = setup["journal_entry"]
        debit_tx, credit_tx = self.add_transactions(
            journal_entry,
            debit_account=setup["expense_account"],
            credit_account=setup["cash_account"],
        )
        expected_tx_ids = [debit_tx.uuid, credit_tx.uuid]

        with_accounts_qs = journal_entry.get_transaction_queryset(select_accounts=True)
        without_accounts_qs = journal_entry.get_transaction_queryset(select_accounts=False)

        self.assertCountEqual(
            expected_tx_ids,
            list(with_accounts_qs.values_list("uuid", flat=True)),
        )
        self.assertCountEqual(
            expected_tx_ids,
            list(without_accounts_qs.values_list("uuid", flat=True)),
        )

    def test_get_txs_balances_returns_debit_and_credit_totals(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Validation Balances Entity",
        )
        journal_entry = setup["journal_entry"]
        self.add_transactions(
            journal_entry,
            debit_account=setup["expense_account"],
            credit_account=setup["cash_account"],
        )

        balance_dict = journal_entry.get_txs_balances(as_dict=True)
        balance_rows = journal_entry.get_txs_balances(as_dict=False)
        balance_row_dict = {
            row["tx_type"]: row["amount__sum"]
            for row in balance_rows
        }

        self.assertEqual(Decimal("100.00"), balance_dict[TransactionModel.DEBIT])
        self.assertEqual(Decimal("100.00"), balance_dict[TransactionModel.CREDIT])
        self.assertEqual(balance_dict, balance_row_dict)

    def test_is_balance_valid_returns_true_for_balanced_transactions(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Validation Balanced Entity",
        )
        journal_entry = setup["journal_entry"]
        self.add_transactions(
            journal_entry,
            debit_account=setup["expense_account"],
            credit_account=setup["cash_account"],
        )

        self.assertTrue(journal_entry.is_balance_valid(journal_entry.get_transaction_queryset()))

    def test_is_balance_valid_returns_false_without_raising_for_imbalanced_transactions(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Validation Imbalanced No Raise Entity",
        )
        journal_entry = setup["journal_entry"]
        self.add_transactions(
            journal_entry,
            debit_account=setup["expense_account"],
            credit_account=setup["cash_account"],
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("90.00"),
        )

        self.assertFalse(
            journal_entry.is_balance_valid(
                journal_entry.get_transaction_queryset(),
                raise_exception=False,
            )
        )

    def test_is_balance_valid_raises_for_imbalanced_transactions_by_default(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Validation Imbalanced Raise Entity",
        )
        journal_entry = setup["journal_entry"]
        self.add_transactions(
            journal_entry,
            debit_account=setup["expense_account"],
            credit_account=setup["cash_account"],
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("90.00"),
        )

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.is_balance_valid(journal_entry.get_transaction_queryset())

    def test_is_txs_qs_valid_accepts_this_entries_transaction_queryset(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Validation Own QuerySet Entity",
        )
        journal_entry = setup["journal_entry"]
        self.add_transactions(
            journal_entry,
            debit_account=setup["expense_account"],
            credit_account=setup["cash_account"],
        )

        self.assertTrue(journal_entry.is_txs_qs_valid(journal_entry.get_transaction_queryset()))

    def test_is_txs_qs_valid_rejects_another_entries_transaction_queryset(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Validation Other QuerySet Entity",
        )
        journal_entry = setup["journal_entry"]
        other_journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Validation Other Journal Entry",
        )
        self.add_transactions(
            other_journal_entry,
            debit_account=setup["expense_account"],
            credit_account=setup["cash_account"],
        )

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.is_txs_qs_valid(other_journal_entry.get_transaction_queryset())

    def test_is_txs_qs_coa_valid_accepts_transactions_from_one_coa(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Validation One CoA Entity",
        )
        journal_entry = setup["journal_entry"]
        self.add_transactions(
            journal_entry,
            debit_account=setup["expense_account"],
            credit_account=setup["cash_account"],
        )

        self.assertTrue(journal_entry.is_txs_qs_coa_valid(journal_entry.get_transaction_queryset()))

    def test_is_txs_qs_coa_valid_rejects_transactions_spanning_multiple_coas(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Validation Mixed CoA Entity",
        )
        entity_model = setup["entity_model"]
        other_coa_model = entity_model.create_chart_of_accounts(
            coa_name="API JE Validation Other CoA",
            commit=True,
            assign_as_default=False,
        )
        other_cash_account = other_coa_model.create_account(
            code="1010",
            name="API JE Validation Other Cash",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )
        journal_entry = setup["journal_entry"]
        self.add_transactions(
            journal_entry,
            debit_account=setup["expense_account"],
            credit_account=other_cash_account,
        )

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.is_txs_qs_coa_valid(journal_entry.get_transaction_queryset())
