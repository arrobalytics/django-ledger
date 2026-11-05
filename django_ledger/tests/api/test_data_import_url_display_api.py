"""
High-level API smoke tests for data import URL and display helpers.

ImportJobModel URL helpers are covered in the dedicated import job helper
suite; this file focuses on the remaining StagedTransactionModel helpers.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, CREDIT, DEBIT
from django_ledger.models import BankAccountModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.receipt import ReceiptModel


class DataImportURLDisplayAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_data_import_url_admin",
            email="api-data-import-url-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Data Import URL Entity"):
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
            "customer_model": customer_model,
            "import_job": import_job,
        }

    def create_staged_transaction(self, setup, *, fit_id="FIT-URL", amount="125.00"):
        staged_tx = StagedTransactionModel.objects.create(
            import_job=setup["import_job"],
            fit_id=fit_id,
            date_posted=date(2026, 1, 15),
            amount=Decimal(amount),
            name=f"API Staged Transaction {fit_id}",
            memo=f"API staged transaction memo {fit_id}",
            account_model=setup["income_account"],
        )
        return StagedTransactionModel.objects.get(uuid=staged_tx.uuid)

    def test_staged_transaction_get_update_url_contains_entity_job_and_staged_transaction_ids(self):
        setup = self.create_entity_setup()
        staged_tx = self.create_staged_transaction(setup)

        url = staged_tx.get_update_url()

        self.assertIsInstance(url, str)
        self.assertTrue(url)
        self.assertIn(setup["entity_model"].slug, url)
        self.assertIn(str(setup["import_job"].uuid), url)
        self.assertIn(str(staged_tx.uuid), url)

    def test_staged_transaction_str_includes_amount_context(self):
        setup = self.create_entity_setup(name="API Data Import String Entity")
        staged_tx = self.create_staged_transaction(setup, amount="-75.00")

        display_value = str(staged_tx)

        self.assertIsInstance(display_value, str)
        self.assertTrue(display_value)
        self.assertIn("StagedTransactionModel", display_value)
        self.assertIn("-75.00", display_value)

    def test_entity_slug_annotation_and_get_entity_slug_helper(self):
        setup = self.create_entity_setup(name="API Data Import Entity Slug Entity")
        staged_tx = self.create_staged_transaction(setup)

        self.assertEqual(staged_tx.entity_slug, setup["entity_model"].slug)
        self.assertEqual(staged_tx.get_entity_slug(), setup["entity_model"].slug)

    def test_receipt_uuid_annotation_and_fallback_behavior(self):
        setup = self.create_entity_setup(name="API Data Import Receipt UUID Entity")
        staged_tx = self.create_staged_transaction(setup)

        self.assertIsNone(staged_tx.receipt_uuid)

        staged_tx.receipt_type = ReceiptModel.SALES_RECEIPT
        staged_tx.customer_model = setup["customer_model"]
        staged_tx.save(update_fields=["receipt_type", "customer_model", "updated"])
        staged_tx = StagedTransactionModel.objects.get(uuid=staged_tx.uuid)
        receipt_model = staged_tx.generate_receipt_model(
            receipt_date=date(2026, 1, 15),
            commit=True,
        )
        staged_tx = StagedTransactionModel.objects.get(uuid=staged_tx.uuid)

        self.assertEqual(staged_tx.receipt_uuid, receipt_model.uuid)
