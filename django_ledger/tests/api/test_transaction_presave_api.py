"""
High-level API behavior tests for TransactionModel pre-save guards.

These tests cover account transactionability and update-time journal-entry
locking behavior without duplicating the basic invariant tests.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.transactions import TransactionModelValidationError


class TransactionPreSaveAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_tx_presave_admin",
            email="api-tx-presave-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_setup(self, *, name="API Transaction PreSave Entity"):
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
            "cash_account": cash_account,
            "expense_account": expense_account,
            "journal_entry": journal_entry,
        }

    def create_transaction(
        self,
        setup,
        *,
        account=None,
        amount=Decimal("10.00"),
        description="API Transaction PreSave Transaction",
    ):
        return TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=setup["journal_entry"],
            account=account or setup["expense_account"],
            amount=amount,
            description=description,
        )

    def test_valid_transaction_on_transactable_account_is_accepted(self):
        setup = self.create_entity_setup(name="API TX Valid PreSave Entity")

        transaction_model = self.create_transaction(
            setup,
            account=setup["expense_account"],
            amount=Decimal("25.00"),
            description="API TX Valid PreSave",
        )

        self.assertTrue(TransactionModel.objects.filter(uuid=transaction_model.uuid).exists())
        self.assertEqual(Decimal("25.00"), transaction_model.amount)

    def test_locked_account_rejects_new_transaction(self):
        setup = self.create_entity_setup(name="API TX Locked Account Entity")
        setup["expense_account"].lock(commit=True)

        with self.assertRaises(TransactionModelValidationError):
            self.create_transaction(
                setup,
                account=setup["expense_account"],
                description="API TX Locked Account Rejected",
            )

    def test_updating_existing_transaction_after_journal_entry_becomes_locked_is_rejected(self):
        setup = self.create_entity_setup(name="API TX Locked JE Update Entity")
        transaction_model = self.create_transaction(
            setup,
            description="API TX Locked JE Update",
        )
        setup["journal_entry"].locked = True
        setup["journal_entry"].save(verify=False, update_fields=["locked", "updated"])

        transaction_model.amount = Decimal("30.00")
        with self.assertRaises(TransactionModelValidationError):
            transaction_model.save(update_fields=["amount", "updated"])

        transaction_model.refresh_from_db()
        self.assertEqual(Decimal("10.00"), transaction_model.amount)

    def test_updating_existing_transaction_after_journal_entry_becomes_posted_is_rejected(self):
        setup = self.create_entity_setup(name="API TX Posted JE Update Entity")
        transaction_model = self.create_transaction(
            setup,
            description="API TX Posted JE Update",
        )
        JournalEntryModel.objects.filter(uuid=setup["journal_entry"].uuid).update(posted=True)
        transaction_model = TransactionModel.objects.get(uuid=transaction_model.uuid)

        transaction_model.amount = Decimal("30.00")
        with self.assertRaises(TransactionModelValidationError):
            transaction_model.save(update_fields=["amount", "updated"])

        transaction_model.refresh_from_db()
        self.assertEqual(Decimal("10.00"), transaction_model.amount)
