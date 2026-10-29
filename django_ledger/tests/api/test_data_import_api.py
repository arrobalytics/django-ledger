"""
High-level API behavior tests for ImportJobModel and StagedTransactionModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import BankAccountModel, JournalEntryModel, TransactionModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.data_import import (
    ImportJobModel,
    ImportJobModelValidationError,
    StagedTransactionModel,
    StagedTransactionModelValidationError,
)
from django_ledger.models.entity import EntityModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.unit import EntityUnitModel
from django_ledger.models.vendor import VendorModel


class DataImportHighLevelAPITest(TestCase):
    """
    High-level behavior tests for data import and staged transaction contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic import/staging invariants that should
    remain true across swappable-model refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_data_import_contract_user",
            email="api-data-import-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Data Import Contract Entity"):
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

        income_account = coa_model.create_account(
            code="4010",
            name=f"{name} Income Account",
            role="in_operational",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        bank_account = BankAccountModel(
            name=f"{name} Bank Account",
            account_model=cash_account,
            account_number="000123456789",
            routing_number="000111000",
            active=True,
            hidden=False,
        )
        bank_account.configure(
            entity_slug=entity_model,
            user_model=self.user,
            commit=True,
        )

        customer_model = CustomerModel(
            customer_name=f"{name} Customer",
            entity_model=entity_model,
            description=f"{name} Customer description",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()

        vendor_model = VendorModel(
            vendor_name=f"{name} Vendor",
            entity_model=entity_model,
            description=f"{name} Vendor description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()

        unit_model = EntityUnitModel.add_root(
            name=f"{name} Unit",
            slug="api-data-import-unit",
            entity=entity_model,
            document_prefix="DIU",
            active=True,
            hidden=False,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "income_account": income_account,
            "expense_account": expense_account,
            "bank_account": bank_account,
            "customer_model": customer_model,
            "vendor_model": vendor_model,
            "unit_model": unit_model,
        }

    def create_import_job(self, setup, *, description="API Data Import Job"):
        import_job = ImportJobModel.objects.create(
            description=description,
            bank_account_model=setup["bank_account"],
        )

        import_job.configure(commit=True)
        import_job.refresh_from_db()

        return import_job

    def create_staged_transaction(
        self,
        import_job,
        *,
        fit_id="FIT-001",
        amount="125.00",
        date_posted=date(2026, 1, 15),
        name="API Staged Transaction",
        memo="API staged transaction memo",
        account_model=None,
        unit_model=None,
        receipt_type=None,
        customer_model=None,
        vendor_model=None,
        bundle_split=True,
    ):
        staged_tx = StagedTransactionModel.objects.create(
            import_job=import_job,
            fit_id=fit_id,
            date_posted=date_posted,
            amount=Decimal(amount),
            name=name,
            memo=memo,
            account_model=account_model,
            unit_model=unit_model,
            receipt_type=receipt_type,
            customer_model=customer_model,
            vendor_model=vendor_model,
            bundle_split=bundle_split,
        )

        staged_tx.refresh_from_db()
        return staged_tx

    def get_annotated_staged_transaction(self, staged_tx):
        return StagedTransactionModel.objects.get(uuid=staged_tx.uuid)

    def test_import_job_configure_creates_ledger_for_bank_account_entity(self):
        setup = self.create_entity_setup()

        import_job = self.create_import_job(setup)

        self.assertIsInstance(import_job, ImportJobModel)
        self.assertIsNotNone(import_job.uuid)
        self.assertEqual(import_job.bank_account_model_id, setup["bank_account"].uuid)
        self.assertTrue(import_job.is_configured())
        self.assertIsNotNone(import_job.ledger_model_id)
        self.assertEqual(import_job.ledger_model.entity_id, setup["entity_model"].uuid)
        self.assertEqual(import_job.entity_uuid, setup["entity_model"].uuid)
        self.assertEqual(import_job.entity_slug, setup["entity_model"].slug)

    def test_import_job_for_entity_limits_queryset_to_entity_scope(self):
        setup = self.create_entity_setup(name="API Import Entity A")
        other_setup = self.create_entity_setup(name="API Import Entity B")

        import_job = self.create_import_job(setup)
        other_import_job = self.create_import_job(other_setup)

        scoped_qs = ImportJobModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(scoped_qs.filter(uuid=import_job.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_import_job.uuid).exists())

    def test_import_job_annotations_reflect_pending_root_transactions(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        self.create_staged_transaction(
            import_job,
            fit_id="FIT-PENDING-001",
            amount="125.00",
        )

        annotated_job = ImportJobModel.objects.get(uuid=import_job.uuid)

        self.assertEqual(annotated_job.txs_count, 1)
        self.assertEqual(annotated_job.txs_imported_count, 0)
        self.assertEqual(annotated_job.txs_pending, 1)
        self.assertFalse(annotated_job.is_complete)

    def test_staged_transaction_for_entity_and_import_job_querysets(self):
        setup = self.create_entity_setup()
        other_setup = self.create_entity_setup(name="API Other Import Entity")

        import_job = self.create_import_job(setup)
        other_import_job = self.create_import_job(other_setup)

        staged_tx = self.create_staged_transaction(import_job, fit_id="FIT-A")
        other_staged_tx = self.create_staged_transaction(other_import_job, fit_id="FIT-B")

        entity_qs = StagedTransactionModel.objects.for_entity(setup["entity_model"])
        import_job_qs = StagedTransactionModel.objects.for_import_job(import_job)

        self.assertTrue(entity_qs.filter(uuid=staged_tx.uuid).exists())
        self.assertFalse(entity_qs.filter(uuid=other_staged_tx.uuid).exists())

        self.assertTrue(import_job_qs.filter(uuid=staged_tx.uuid).exists())
        self.assertFalse(import_job_qs.filter(uuid=other_staged_tx.uuid).exists())

    def test_single_mapped_non_receipt_staged_transaction_is_ready_to_import(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-READY-001",
            amount="125.00",
            account_model=setup["income_account"],
            unit_model=setup["unit_model"],
            receipt_type=None,
            customer_model=None,
            vendor_model=None,
        )

        staged_tx = StagedTransactionModel.objects.get(uuid=staged_tx.uuid)

        self.assertTrue(staged_tx.is_single())
        self.assertTrue(staged_tx.is_parent())
        self.assertFalse(staged_tx.is_children())
        self.assertFalse(staged_tx.has_receipt())
        self.assertTrue(staged_tx.is_mapped())
        self.assertTrue(staged_tx.ready_to_import)
        self.assertTrue(staged_tx.can_import())

    def test_sales_staged_transaction_clears_vendor_on_clean(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = StagedTransactionModel(
            import_job=import_job,
            fit_id="FIT-SALES-001",
            date_posted=date(2026, 1, 15),
            amount=Decimal("125.00"),
            account_model=setup["income_account"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            customer_model=setup["customer_model"],
            vendor_model=setup["vendor_model"],
        )

        staged_tx.clean()

        self.assertTrue(staged_tx.is_sales())
        self.assertEqual(staged_tx.customer_model_id, setup["customer_model"].uuid)
        self.assertIsNone(staged_tx.vendor_model)

    def test_expense_staged_transaction_clears_customer_on_clean(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = StagedTransactionModel(
            import_job=import_job,
            fit_id="FIT-EXPENSE-001",
            date_posted=date(2026, 1, 15),
            amount=Decimal("-75.00"),
            account_model=setup["expense_account"],
            receipt_type=ReceiptModel.EXPENSE_RECEIPT,
            vendor_model=setup["vendor_model"],
            customer_model=setup["customer_model"],
        )

        staged_tx.clean()

        self.assertTrue(staged_tx.is_expense())
        self.assertEqual(staged_tx.vendor_model_id, setup["vendor_model"].uuid)
        self.assertIsNone(staged_tx.customer_model)

    def test_transfer_staged_transaction_clears_customer_and_vendor_on_clean(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = StagedTransactionModel(
            import_job=import_job,
            fit_id="FIT-TRANSFER-001",
            date_posted=date(2026, 1, 15),
            amount=Decimal("50.00"),
            account_model=setup["cash_account"],
            receipt_type=ReceiptModel.TRANSFER_RECEIPT,
            customer_model=setup["customer_model"],
            vendor_model=setup["vendor_model"],
        )

        staged_tx.clean()

        self.assertTrue(staged_tx.is_transfer())
        self.assertIsNone(staged_tx.customer_model)
        self.assertIsNone(staged_tx.vendor_model)

    def test_staged_transaction_presave_rejects_customer_and_vendor_together(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        with self.assertRaises(StagedTransactionModelValidationError):
            self.create_staged_transaction(
                import_job,
                fit_id="FIT-BOTH-PARTIES-001",
                amount="125.00",
                account_model=setup["income_account"],
                receipt_type=ReceiptModel.SALES_RECEIPT,
                customer_model=setup["customer_model"],
                vendor_model=setup["vendor_model"],
            )

    def test_staged_transaction_add_split_creates_children(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-SPLIT-001",
            amount="100.00",
            account_model=setup["income_account"],
        )

        staged_tx = self.get_annotated_staged_transaction(staged_tx)
        children = staged_tx.add_split(n=1, commit=True)

        staged_tx = StagedTransactionModel.objects.get(uuid=staged_tx.uuid)

        self.assertEqual(len(children), 2)
        self.assertTrue(staged_tx.has_children())
        self.assertFalse(staged_tx.is_single())

        child_qs = StagedTransactionModel.objects.filter(parent=staged_tx)

        self.assertEqual(child_qs.count(), 2)

        for child in child_qs:
            self.assertTrue(child.is_children())
            self.assertFalse(child.is_parent())
            self.assertEqual(child.import_job_id, import_job.uuid)
            self.assertEqual(child.fit_id, staged_tx.fit_id)
            self.assertEqual(child.amount_split, Decimal("0.00"))

    def test_parent_staged_transaction_cannot_be_deleted(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-DELETE-PARENT-001",
            amount="100.00",
        )

        with self.assertRaises(StagedTransactionModelValidationError):
            staged_tx.delete()

    def test_child_staged_transaction_can_be_deleted(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-DELETE-CHILD-001",
            amount="100.00",
        )
        staged_tx = self.get_annotated_staged_transaction(staged_tx)
        children = staged_tx.add_split(n=1, commit=True)

        child = children[0]
        child_uuid = child.uuid

        child.delete()

        self.assertFalse(StagedTransactionModel.objects.filter(uuid=child_uuid).exists())

    def test_staged_transaction_migrate_transactions_creates_unposted_journal_entry_and_links_transaction(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-MIGRATE-JE-001",
            amount="125.00",
            account_model=setup["income_account"],
            unit_model=setup["unit_model"],
            receipt_type=None,
            customer_model=None,
            vendor_model=None,
        )

        staged_tx = self.get_annotated_staged_transaction(staged_tx)

        self.assertTrue(staged_tx.ready_to_import)
        self.assertTrue(staged_tx.can_import())

        staged_tx.migrate_transactions()

        staged_tx.refresh_from_db()

        self.assertIsNotNone(staged_tx.transaction_model_id)

        journal_entries = JournalEntryModel.objects.filter(
            ledger=import_job.ledger_model,
        )

        self.assertEqual(journal_entries.count(), 1)

        journal_entry = journal_entries.get()

        self.assertFalse(journal_entry.posted)
        self.assertEqual(journal_entry.entity_unit_id, setup["unit_model"].uuid)

        txs = TransactionModel.objects.filter(journal_entry=journal_entry)

        self.assertEqual(txs.count(), 2)
        self.assertEqual(
            sum(tx.amount for tx in txs if tx.tx_type == TransactionModel.DEBIT),
            Decimal("125.00"),
        )
        self.assertEqual(
            sum(tx.amount for tx in txs if tx.tx_type == TransactionModel.CREDIT),
            Decimal("125.00"),
        )

    def test_staged_transaction_migrate_transactions_rejects_receipt_transaction(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-MIGRATE-JE-RECEIPT-001",
            amount="125.00",
            account_model=setup["income_account"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            customer_model=setup["customer_model"],
        )

        staged_tx = self.get_annotated_staged_transaction(staged_tx)

        with self.assertRaises(StagedTransactionModelValidationError):
            staged_tx.migrate_transactions()

    def test_staged_transaction_migrate_receipt_creates_receipt_and_posted_journal_entry(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-MIGRATE-RECEIPT-001",
            amount="125.00",
            account_model=setup["income_account"],
            unit_model=setup["unit_model"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            customer_model=setup["customer_model"],
        )

        staged_tx = self.get_annotated_staged_transaction(staged_tx)

        self.assertTrue(staged_tx.ready_to_import)
        self.assertTrue(staged_tx.can_migrate_receipt())

        staged_tx.migrate_receipt(
            receipt_date=date(2026, 1, 15),
            split_amount=False,
        )

        staged_tx.refresh_from_db()

        receipt_model = ReceiptModel.objects.get(
            staged_transaction_model=staged_tx,
        )

        self.assertEqual(receipt_model.receipt_type, ReceiptModel.SALES_RECEIPT)
        self.assertEqual(receipt_model.amount, Decimal("125.00"))
        self.assertEqual(receipt_model.customer_model_id, setup["customer_model"].uuid)
        self.assertIsNone(receipt_model.vendor_model_id)
        self.assertEqual(receipt_model.charge_account_id, setup["cash_account"].uuid)
        self.assertEqual(receipt_model.receipt_account_id, setup["income_account"].uuid)
        self.assertEqual(receipt_model.unit_model_id, setup["unit_model"].uuid)
        self.assertTrue(receipt_model.receipt_number)

        self.assertTrue(receipt_model.ledger_model.is_posted())

        journal_entries = JournalEntryModel.objects.filter(
            ledger=receipt_model.ledger_model,
        )

        self.assertEqual(journal_entries.count(), 1)

        journal_entry = journal_entries.get()

        self.assertTrue(journal_entry.posted)
        self.assertEqual(journal_entry.entity_unit_id, setup["unit_model"].uuid)

        txs = TransactionModel.objects.filter(journal_entry=journal_entry)

        self.assertEqual(txs.count(), 2)
        self.assertEqual(
            sum(tx.amount for tx in txs if tx.tx_type == TransactionModel.DEBIT),
            Decimal("125.00"),
        )
        self.assertEqual(
            sum(tx.amount for tx in txs if tx.tx_type == TransactionModel.CREDIT),
            Decimal("125.00"),
        )

        self.assertIsNotNone(staged_tx.transaction_model_id)

    def test_staged_transaction_migrate_receipt_rejects_non_receipt_transaction(self):
        setup = self.create_entity_setup()
        import_job = self.create_import_job(setup)

        staged_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-MIGRATE-RECEIPT-NON-RECEIPT-001",
            amount="125.00",
            account_model=setup["income_account"],
            receipt_type=None,
            customer_model=None,
            vendor_model=None,
        )

        staged_tx = self.get_annotated_staged_transaction(staged_tx)

        with self.assertRaises(StagedTransactionModelValidationError):
            staged_tx.migrate_receipt(
                receipt_date=date(2026, 1, 15),
            )

