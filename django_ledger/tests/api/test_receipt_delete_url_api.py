"""
High-level API tests for ReceiptModel delete guards and URL helpers.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import ReceiptModel
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.receipt import ReceiptModelValidationError
from django_ledger.models.vendor import VendorModel


class ReceiptDeleteURLAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_receipt_delete_url_user",
            email="api-receipt-delete-url-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Receipt Delete URL Entity"):
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
        transfer_account = coa_model.create_account(
            code="1020",
            name=f"{name} Transfer Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
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

        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
            "income_account": income_account,
            "expense_account": expense_account,
            "transfer_account": transfer_account,
            "customer_model": customer_model,
            "vendor_model": vendor_model,
        }

    def create_sales_receipt(self, setup, *, receipt_date=date(2026, 1, 15), staged_transaction_model=None):
        receipt_model = ReceiptModel()
        receipt_model.configure(
            entity_model=setup["entity_model"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            amount=Decimal("125.00"),
            receipt_date=receipt_date,
            customer_model=setup["customer_model"],
            charge_account=setup["cash_account"],
            receipt_account=setup["income_account"],
            staged_transaction_model=staged_transaction_model,
            commit=True,
        )
        receipt_model.refresh_from_db()
        return receipt_model

    def create_expense_receipt(self, setup):
        receipt_model = ReceiptModel()
        receipt_model.configure(
            entity_model=setup["entity_model"],
            receipt_type=ReceiptModel.EXPENSE_RECEIPT,
            amount=Decimal("75.00"),
            receipt_date=date(2026, 1, 15),
            vendor_model=setup["vendor_model"],
            charge_account=setup["cash_account"],
            receipt_account=setup["expense_account"],
            commit=True,
        )
        receipt_model.refresh_from_db()
        return receipt_model

    def create_transfer_receipt(self, setup):
        receipt_model = ReceiptModel()
        receipt_model.configure(
            entity_model=setup["entity_model"],
            receipt_type=ReceiptModel.TRANSFER_RECEIPT,
            amount=Decimal("50.00"),
            receipt_date=date(2026, 1, 15),
            charge_account=setup["cash_account"],
            receipt_account=setup["transfer_account"],
            commit=True,
        )
        receipt_model.refresh_from_db()
        return receipt_model

    def set_last_closing_date(self, entity_model, closing_date):
        entity_model.last_closing_date = closing_date
        entity_model.save(update_fields=["last_closing_date"])

    def create_staged_transaction(self, setup):
        bank_account = BankAccountModel.objects.create(
            name="API Receipt URL Bank Account",
            account_type=BankAccountModel.ACCOUNT_CHECKING,
            account_number="123456789",
            routing_number="123456789",
            aba_number="123456789",
            entity_model=setup["entity_model"],
            account_model=setup["cash_account"],
            active=True,
        )
        import_job = ImportJobModel.objects.create(
            description="API Receipt URL Import Job",
            bank_account_model=bank_account,
        )
        import_job.configure(commit=True)
        return StagedTransactionModel.objects.create(
            import_job=import_job,
            fit_id="FIT-RECEIPT-URL",
            date_posted=date(2026, 1, 15),
            amount=Decimal("125.00"),
            name="API Receipt URL Staged Transaction",
            memo="API receipt URL staged transaction memo",
            account_model=setup["income_account"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            customer_model=setup["customer_model"],
        )

    def test_can_delete_reflects_entity_closing_date_boundaries(self):
        setup = self.create_entity_setup()
        receipt_model = self.create_sales_receipt(setup, receipt_date=date(2026, 1, 15))

        self.assertTrue(ReceiptModel.objects.get(uuid=receipt_model.uuid).can_delete())

        self.set_last_closing_date(setup["entity_model"], date(2026, 1, 14))
        self.assertTrue(ReceiptModel.objects.get(uuid=receipt_model.uuid).can_delete())

        self.set_last_closing_date(setup["entity_model"], date(2026, 1, 15))
        self.assertFalse(ReceiptModel.objects.get(uuid=receipt_model.uuid).can_delete())

        self.set_last_closing_date(setup["entity_model"], date(2026, 1, 16))
        self.assertFalse(ReceiptModel.objects.get(uuid=receipt_model.uuid).can_delete())

    def test_delete_success_removes_receipt_and_journal_entries_but_leaves_ledger(self):
        setup = self.create_entity_setup(name="API Receipt Delete Success Entity")
        receipt_model = self.create_sales_receipt(setup)
        ledger_model = receipt_model.ledger_model
        journal_entry = JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
            description="API Receipt Delete Journal Entry",
        )

        receipt_model.delete()

        self.assertFalse(ReceiptModel.objects.filter(uuid=receipt_model.uuid).exists())
        self.assertFalse(JournalEntryModel.objects.filter(uuid=journal_entry.uuid).exists())
        self.assertTrue(ledger_model.__class__.objects.filter(uuid=ledger_model.uuid).exists())

    def test_delete_rejects_closed_period_and_leaves_receipt_intact(self):
        setup = self.create_entity_setup(name="API Receipt Delete Closed Entity")
        receipt_model = self.create_sales_receipt(setup, receipt_date=date(2026, 1, 15))
        self.set_last_closing_date(setup["entity_model"], date(2026, 1, 15))
        receipt_model = ReceiptModel.objects.get(uuid=receipt_model.uuid)

        with self.assertRaises(ReceiptModelValidationError):
            receipt_model.delete()

        self.assertTrue(ReceiptModel.objects.filter(uuid=receipt_model.uuid).exists())

    def test_url_helpers_return_entity_scoped_strings_or_none(self):
        setup = self.create_entity_setup(name="API Receipt URL Helper Entity")
        sales_receipt = self.create_sales_receipt(setup)
        expense_receipt = self.create_expense_receipt(setup)
        transfer_receipt = self.create_transfer_receipt(setup)
        entity_slug = setup["entity_model"].slug

        absolute_url = sales_receipt.get_absolute_url()
        self.assertIsInstance(absolute_url, str)
        self.assertIn(entity_slug, absolute_url)
        self.assertIn(str(sales_receipt.uuid), absolute_url)

        list_url = sales_receipt.get_list_url()
        self.assertIsInstance(list_url, str)
        self.assertIn(entity_slug, list_url)
        self.assertNotIn(str(sales_receipt.uuid), list_url)

        delete_url = sales_receipt.get_delete_url()
        self.assertIsInstance(delete_url, str)
        self.assertIn(entity_slug, delete_url)
        self.assertIn(str(sales_receipt.uuid), delete_url)

        customer_list_url = sales_receipt.get_customer_list_url()
        customer_report_url = sales_receipt.get_customer_report_url()
        self.assertIsInstance(customer_list_url, str)
        self.assertIsInstance(customer_report_url, str)
        self.assertIn(entity_slug, customer_list_url)
        self.assertIn(str(setup["customer_model"].uuid), customer_list_url)
        self.assertIn(entity_slug, customer_report_url)
        self.assertIsNone(sales_receipt.get_vendor_list_url())
        self.assertIsNone(sales_receipt.get_vendor_report_url())

        vendor_list_url = expense_receipt.get_vendor_list_url()
        vendor_report_url = expense_receipt.get_vendor_report_url()
        self.assertIsInstance(vendor_list_url, str)
        self.assertIsInstance(vendor_report_url, str)
        self.assertIn(entity_slug, vendor_list_url)
        self.assertIn(str(setup["vendor_model"].uuid), vendor_list_url)
        self.assertIn(entity_slug, vendor_report_url)
        self.assertIsNone(expense_receipt.get_customer_list_url())
        self.assertIsNone(expense_receipt.get_customer_report_url())

        self.assertIsNone(transfer_receipt.get_customer_list_url())
        self.assertIsNone(transfer_receipt.get_vendor_list_url())
        self.assertIsNone(transfer_receipt.get_customer_report_url())
        self.assertIsNone(transfer_receipt.get_vendor_report_url())

    def test_import_job_and_staged_transaction_url_helpers_return_none_or_related_urls(self):
        setup = self.create_entity_setup(name="API Receipt Import URL Entity")
        receipt_without_import = self.create_sales_receipt(setup)

        self.assertIsNone(receipt_without_import.get_import_job_url())
        self.assertIsNone(receipt_without_import.get_staged_tx_url())

        staged_tx = self.create_staged_transaction(setup)
        receipt_with_import = self.create_sales_receipt(setup, staged_transaction_model=staged_tx)

        import_job_url = receipt_with_import.get_import_job_url()
        staged_tx_url = receipt_with_import.get_staged_tx_url()

        self.assertIsInstance(import_job_url, str)
        self.assertIn(setup["entity_model"].slug, import_job_url)
        self.assertIn(str(staged_tx.import_job_id), import_job_url)

        self.assertIsInstance(staged_tx_url, str)
        self.assertIn(import_job_url, staged_tx_url)
        self.assertIn(str(staged_tx.uuid), staged_tx_url)
