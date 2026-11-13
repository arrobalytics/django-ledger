"""
High-level API tests for staged transaction import and undo helpers.

These tests cover migration/undo behavior from StagedTransactionModel without
testing matching internals, upload flows, or OFX parsing.
"""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, CREDIT, DEBIT
from django_ledger.models import BankAccountModel, JournalEntryModel, TransactionModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.data_import import (
    ImportJobModel,
    StagedTransactionModel,
    StagedTransactionModelValidationError,
)
from django_ledger.models.entity import EntityModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.unit import EntityUnitModel


class StagedTransactionImportUndoAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_staged_import_undo_admin",
            email="api-staged-import-undo-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Staged Import Undo Entity"):
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
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        income_account = coa_model.create_account(
            code="4010",
            name=f"{name} Income",
            role="in_operational",
            balance_type=CREDIT,
            active=True,
        )
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense",
            role="ex_regular",
            balance_type=DEBIT,
            active=True,
        )
        bank_account = BankAccountModel(
            name=f"{name} Bank Account",
            account_model=cash_account,
            account_number="000123456789",
            routing_number="000111000",
            active=True,
        )
        bank_account.configure(entity_slug=entity_model, user_model=self.admin_user, commit=True)
        customer_model = CustomerModel.objects.create(
            customer_name=f"{name} Customer",
            entity_model=entity_model,
            active=True,
        )
        unit_model = EntityUnitModel.add_root(
            name=f"{name} Unit",
            slug=f"{name.lower().replace(' ', '-')}-unit",
            entity=entity_model,
            document_prefix="SIU",
            active=True,
        )
        import_job = ImportJobModel.objects.create(
            description=f"{name} Import Job",
            bank_account_model=bank_account,
        )
        import_job.configure(commit=True)
        import_job.refresh_from_db()
        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
            "income_account": income_account,
            "expense_account": expense_account,
            "bank_account": bank_account,
            "customer_model": customer_model,
            "unit_model": unit_model,
            "import_job": import_job,
        }

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_staged_transaction(
        self,
        setup,
        *,
        fit_id="FIT-IMPORT",
        amount="125.00",
        account_model=None,
        unit_model=None,
        receipt_type=None,
        customer_model=None,
        parent=None,
        amount_split=None,
        bundle_split=True,
        transaction_model=None,
    ):
        staged_tx = StagedTransactionModel.objects.create(
            import_job=setup["import_job"],
            parent=parent,
            fit_id=fit_id,
            date_posted=date(2026, 1, 15),
            amount=None if parent else Decimal(amount),
            amount_split=amount_split,
            name=f"API Staged Transaction {fit_id}",
            memo=f"API staged transaction memo {fit_id}",
            account_model=account_model,
            unit_model=unit_model,
            receipt_type=receipt_type,
            customer_model=customer_model,
            bundle_split=bundle_split,
            transaction_model=transaction_model,
        )
        return StagedTransactionModel.objects.get(uuid=staged_tx.uuid)

    def test_undo_import_removes_generated_journal_entry_and_unlinks_transaction(self):
        setup = self.create_entity_setup()
        staged_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-UNDO-JE",
            account_model=setup["income_account"],
            unit_model=setup["unit_model"],
        )

        staged_tx.migrate_transactions()
        staged_tx.refresh_from_db()
        transaction_uuid = staged_tx.transaction_model_id
        journal_entry_uuid = staged_tx.transaction_model.journal_entry_id

        self.assertTrue(staged_tx.can_undo_import())

        staged_tx.undo_import()
        staged_tx.refresh_from_db()

        self.assertIsNone(staged_tx.transaction_model_id)
        self.assertFalse(TransactionModel.objects.filter(uuid=transaction_uuid).exists())
        self.assertFalse(JournalEntryModel.objects.filter(uuid=journal_entry_uuid).exists())

    def test_undo_import_removes_generated_receipt_and_unlinks_transaction(self):
        setup = self.create_entity_setup(name="API Staged Undo Receipt Entity")
        staged_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-UNDO-RECEIPT",
            account_model=setup["income_account"],
            unit_model=setup["unit_model"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            customer_model=setup["customer_model"],
        )

        staged_tx.migrate_receipt(receipt_date=date(2026, 1, 15))
        staged_tx.refresh_from_db()
        receipt_uuid = staged_tx.receiptmodel.uuid

        self.assertTrue(staged_tx.can_undo_import())

        staged_tx.undo_import()
        staged_tx.refresh_from_db()

        self.assertIsNone(staged_tx.transaction_model_id)
        self.assertFalse(ReceiptModel.objects.filter(uuid=receipt_uuid).exists())

    def test_undo_import_rejects_pending_transaction_by_default(self):
        setup = self.create_entity_setup(name="API Staged Undo Pending Entity")
        staged_tx = self.create_staged_transaction(setup, fit_id="FIT-UNDO-PENDING")

        self.assertFalse(staged_tx.can_undo_import())
        with self.assertRaises(StagedTransactionModelValidationError):
            staged_tx.undo_import()

    def test_can_undo_import_false_for_bundled_child(self):
        setup = self.create_entity_setup(name="API Staged Undo Child Entity")
        parent_tx = self.create_staged_transaction(setup, fit_id="FIT-UNDO-CHILD")
        parent_tx.add_split(n=1, commit=True)
        child_tx = StagedTransactionModel.objects.filter(parent=parent_tx).first()
        journal_entry = JournalEntryModel.objects.create(
            ledger=setup["import_job"].ledger_model,
            timestamp=self.make_timestamp(),
            description="API Staged Undo Child JE",
        )
        transaction_model = TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=setup["cash_account"],
            amount=Decimal("10.00"),
        )
        child_tx.transaction_model = transaction_model
        child_tx.save(update_fields=["transaction_model", "updated"])
        child_tx = StagedTransactionModel.objects.get(uuid=child_tx.uuid)

        self.assertTrue(child_tx.is_children())
        self.assertTrue(child_tx.is_bundled())
        self.assertFalse(child_tx.can_undo_import())

    def test_migrate_transactions_with_split_txs_links_child_transactions(self):
        setup = self.create_entity_setup(name="API Staged Split Import Entity")
        parent_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-SPLIT-IMPORT",
            amount="100.00",
        )
        parent_tx.add_split(n=1, commit=True)
        children = list(StagedTransactionModel.objects.filter(parent=parent_tx))
        children[0].amount_split = Decimal("60.00")
        children[0].account_model = setup["income_account"]
        children[0].unit_model = setup["unit_model"]
        children[0].save(update_fields=["amount_split", "account_model", "unit_model", "updated"])
        children[1].amount_split = Decimal("40.00")
        children[1].account_model = setup["expense_account"]
        children[1].unit_model = setup["unit_model"]
        children[1].save(update_fields=["amount_split", "account_model", "unit_model", "updated"])
        parent_tx = StagedTransactionModel.objects.get(uuid=parent_tx.uuid)

        self.assertTrue(parent_tx.can_import())
        parent_tx.migrate_transactions(split_txs=True)

        parent_tx.refresh_from_db()
        child_transaction_ids = list(
            StagedTransactionModel.objects.filter(parent=parent_tx)
            .values_list("transaction_model_id", flat=True)
        )

        self.assertIsNotNone(parent_tx.transaction_model_id)
        self.assertEqual(len(child_transaction_ids), 2)
        self.assertTrue(all(child_transaction_ids))
