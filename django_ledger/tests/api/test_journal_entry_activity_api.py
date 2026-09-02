"""
High-level API behavior tests for JournalEntryModel activity classification.

These tests cover role extraction, cash involvement, activity classification,
and generated activity state without exhaustively testing every role group.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io.roles import (
    ASSET_CA_CASH,
    ASSET_PPE_EQUIPMENT,
    EQUITY_CAPITAL,
    EXPENSE_OPERATIONAL,
)
from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.journal_entry import JournalEntryValidationError


class JournalEntryActivityAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_je_activity_admin",
            email="api-je-activity-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_with_activity_accounts(self, *, name="API JE Activity Entity"):
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
            role=ASSET_CA_CASH,
            balance_type="debit",
            active=True,
        )
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense",
            role=EXPENSE_OPERATIONAL,
            balance_type="debit",
            active=True,
        )
        equipment_account = coa_model.create_account(
            code="1510",
            name=f"{name} Equipment",
            role=ASSET_PPE_EQUIPMENT,
            balance_type="debit",
            active=True,
        )
        equity_account = coa_model.create_account(
            code="3010",
            name=f"{name} Equity Capital",
            role=EQUITY_CAPITAL,
            balance_type="credit",
            active=True,
        )
        ledger_model = LedgerModel.objects.create(
            name=f"{name} Ledger",
            ledger_xid=f"{name.lower().replace(' ', '-')}-ledger",
            entity=entity_model,
        )

        return {
            "cash_account": cash_account,
            "expense_account": expense_account,
            "equipment_account": equipment_account,
            "equity_account": equity_account,
            "ledger_model": ledger_model,
        }

    def create_journal_entry(self, ledger_model, *, description="API JE Activity Journal Entry"):
        return JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=self.make_timestamp(),
            description=description,
        )

    def create_transaction(self, journal_entry, *, tx_type, account, amount=Decimal("100.00")):
        return TransactionModel.objects.create(
            tx_type=tx_type,
            journal_entry=journal_entry,
            account=account,
            amount=amount,
            description="Activity transaction.",
        )

    def add_cash_expense_transactions(self, journal_entry, *, cash_account, expense_account):
        self.create_transaction(
            journal_entry,
            tx_type=TransactionModel.DEBIT,
            account=expense_account,
        )
        self.create_transaction(
            journal_entry,
            tx_type=TransactionModel.CREDIT,
            account=cash_account,
        )

    def test_get_txs_roles_returns_involved_account_roles(self):
        setup = self.create_entity_with_activity_accounts(
            name="API JE Activity Roles Entity",
        )
        journal_entry = self.create_journal_entry(setup["ledger_model"])
        self.add_cash_expense_transactions(
            journal_entry,
            cash_account=setup["cash_account"],
            expense_account=setup["expense_account"],
        )

        self.assertEqual(
            {ASSET_CA_CASH, EXPENSE_OPERATIONAL},
            journal_entry.get_txs_roles(),
        )

    def test_get_txs_roles_can_exclude_cash_role(self):
        setup = self.create_entity_with_activity_accounts(
            name="API JE Activity Exclude Cash Entity",
        )
        journal_entry = self.create_journal_entry(setup["ledger_model"])
        self.add_cash_expense_transactions(
            journal_entry,
            cash_account=setup["cash_account"],
            expense_account=setup["expense_account"],
        )

        self.assertEqual(
            {EXPENSE_OPERATIONAL},
            journal_entry.get_txs_roles(exclude_cash_role=True),
        )

    def test_is_cash_involved_is_true_when_cash_transaction_is_present(self):
        setup = self.create_entity_with_activity_accounts(
            name="API JE Activity Cash Involved Entity",
        )
        journal_entry = self.create_journal_entry(setup["ledger_model"])
        self.add_cash_expense_transactions(
            journal_entry,
            cash_account=setup["cash_account"],
            expense_account=setup["expense_account"],
        )

        self.assertTrue(journal_entry.is_cash_involved())

    def test_is_cash_involved_is_false_without_cash_transaction(self):
        setup = self.create_entity_with_activity_accounts(
            name="API JE Activity No Cash Entity",
        )
        journal_entry = self.create_journal_entry(setup["ledger_model"])
        self.create_transaction(
            journal_entry,
            tx_type=TransactionModel.DEBIT,
            account=setup["expense_account"],
        )
        self.create_transaction(
            journal_entry,
            tx_type=TransactionModel.CREDIT,
            account=setup["equity_account"],
        )

        self.assertFalse(journal_entry.is_cash_involved())

    def test_get_activity_from_roles_returns_operating_activity_for_operating_roles(self):
        self.assertEqual(
            JournalEntryModel.OPERATING_ACTIVITY,
            JournalEntryModel.get_activity_from_roles({EXPENSE_OPERATIONAL}),
        )

    def test_get_activity_from_roles_returns_investing_activity_for_investing_roles(self):
        self.assertEqual(
            JournalEntryModel.INVESTING_PPE,
            JournalEntryModel.get_activity_from_roles({ASSET_PPE_EQUIPMENT}),
        )

    def test_get_activity_from_roles_returns_financing_activity_for_financing_roles(self):
        self.assertEqual(
            JournalEntryModel.FINANCING_EQUITY,
            JournalEntryModel.get_activity_from_roles({EQUITY_CAPITAL}),
        )

    def test_get_activity_from_roles_raises_for_mixed_incompatible_activity_roles(self):
        with self.assertRaises(JournalEntryValidationError):
            JournalEntryModel.get_activity_from_roles(
                {EXPENSE_OPERATIONAL, ASSET_PPE_EQUIPMENT},
            )

    def test_generate_activity_sets_activity_for_cash_involved_balanced_entry(self):
        setup = self.create_entity_with_activity_accounts(
            name="API JE Activity Generate Entity",
        )
        journal_entry = self.create_journal_entry(setup["ledger_model"])
        self.add_cash_expense_transactions(
            journal_entry,
            cash_account=setup["cash_account"],
            expense_account=setup["expense_account"],
        )

        activity = journal_entry.generate_activity()

        self.assertEqual(JournalEntryModel.OPERATING_ACTIVITY, activity)
        self.assertEqual(JournalEntryModel.OPERATING_ACTIVITY, journal_entry.activity)

    def test_activity_helpers_reflect_generated_activity(self):
        setup = self.create_entity_with_activity_accounts(
            name="API JE Activity Helper Entity",
        )
        journal_entry = self.create_journal_entry(setup["ledger_model"])
        self.add_cash_expense_transactions(
            journal_entry,
            cash_account=setup["cash_account"],
            expense_account=setup["expense_account"],
        )
        journal_entry.generate_activity()

        self.assertTrue(journal_entry.has_activity())
        self.assertEqual("op", journal_entry.get_activity_name())
        self.assertTrue(journal_entry.is_operating())
        self.assertFalse(journal_entry.is_financing())
        self.assertFalse(journal_entry.is_investing())

        journal_entry.activity = JournalEntryModel.FINANCING_EQUITY
        self.assertEqual("fin", journal_entry.get_activity_name())
        self.assertTrue(journal_entry.is_financing())
        self.assertFalse(journal_entry.is_operating())
        self.assertFalse(journal_entry.is_investing())

        journal_entry.activity = JournalEntryModel.INVESTING_PPE
        self.assertEqual("inv", journal_entry.get_activity_name())
        self.assertTrue(journal_entry.is_investing())
        self.assertFalse(journal_entry.is_operating())
        self.assertFalse(journal_entry.is_financing())
