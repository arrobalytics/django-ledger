"""
High-level API tests for StagedTransactionModel classification helpers.

These tests cover transaction type, mapping, receipt, activity, and capability
helpers without exercising migration, matching, undo, or URL behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, CREDIT, DEBIT
from django_ledger.models import BankAccountModel, JournalEntryModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.unit import EntityUnitModel
from django_ledger.models.vendor import VendorModel


class StagedTransactionClassificationMappingAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_staged_classification_admin",
            email="api-staged-classification-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Staged Classification Entity"):
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
        vendor_model = VendorModel.objects.create(
            vendor_name=f"{name} Vendor",
            entity_model=entity_model,
            active=True,
        )
        unit_model = EntityUnitModel.add_root(
            name=f"{name} Unit",
            slug=f"{name.lower().replace(' ', '-')}-unit",
            entity=entity_model,
            document_prefix="SCM",
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
            "vendor_model": vendor_model,
            "unit_model": unit_model,
            "import_job": import_job,
        }

    def create_staged_transaction(
        self,
        setup,
        *,
        fit_id,
        amount="125.00",
        account_model=None,
        unit_model=None,
        receipt_type=None,
        customer_model=None,
        vendor_model=None,
        activity=None,
        matched_transaction_model=None,
        matched_transaction=False,
    ):
        staged_tx = StagedTransactionModel.objects.create(
            import_job=setup["import_job"],
            fit_id=fit_id,
            date_posted=date(2026, 1, 15),
            amount=Decimal(amount),
            name=f"API Staged Transaction {fit_id}",
            memo=f"API staged transaction memo {fit_id}",
            account_model=account_model,
            unit_model=unit_model,
            receipt_type=receipt_type,
            customer_model=customer_model,
            vendor_model=vendor_model,
            activity=activity,
            matched_transaction_model=matched_transaction_model,
            matched_transaction=matched_transaction,
        )
        return StagedTransactionModel.objects.get(uuid=staged_tx.uuid)

    def test_sales_expense_transfer_and_debt_payment_classification(self):
        setup = self.create_entity_setup()
        sales_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-SALES",
            account_model=setup["income_account"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            customer_model=setup["customer_model"],
        )
        expense_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-EXPENSE",
            amount="-75.00",
            account_model=setup["expense_account"],
            receipt_type=ReceiptModel.EXPENSE_RECEIPT,
            vendor_model=setup["vendor_model"],
        )
        transfer_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-TRANSFER",
            account_model=setup["cash_account"],
            receipt_type=ReceiptModel.TRANSFER_RECEIPT,
        )
        debt_payment_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-DEBT",
            amount="-25.00",
            account_model=setup["expense_account"],
            receipt_type=ReceiptModel.DEBT_PAYMENT,
            vendor_model=setup["vendor_model"],
        )

        self.assertTrue(sales_tx.is_sales())
        self.assertFalse(sales_tx.is_expense())
        self.assertTrue(expense_tx.is_expense())
        self.assertFalse(expense_tx.is_sales())
        self.assertTrue(transfer_tx.is_transfer())
        self.assertTrue(debt_payment_tx.is_debt_payment())

        self.assertEqual(sales_tx.get_amount(), Decimal("125.00"))
        self.assertTrue(sales_tx.is_pending())
        self.assertFalse(sales_tx.is_imported())
        self.assertTrue(sales_tx.is_mapped())

    def test_mapping_capability_helpers_reflect_receipt_and_transaction_type(self):
        setup = self.create_entity_setup()
        sales_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-CAP-SALES",
            account_model=setup["income_account"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            customer_model=setup["customer_model"],
        )
        transfer_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-CAP-TRANSFER",
            account_model=setup["cash_account"],
            receipt_type=ReceiptModel.TRANSFER_RECEIPT,
        )

        self.assertTrue(sales_tx.has_receipt())
        self.assertTrue(sales_tx.has_mapped_receipt())
        self.assertTrue(sales_tx.can_have_receipt())
        self.assertTrue(sales_tx.can_have_customer())
        self.assertFalse(sales_tx.can_have_vendor())
        self.assertTrue(sales_tx.can_have_unit())
        self.assertTrue(sales_tx.can_have_account())
        self.assertTrue(sales_tx.can_have_bundle_split())
        self.assertFalse(sales_tx.can_have_amount_split())

        self.assertTrue(transfer_tx.has_receipt())
        self.assertFalse(transfer_tx.can_have_customer())
        self.assertFalse(transfer_tx.can_have_vendor())
        self.assertFalse(transfer_tx.can_have_bundle_split())
        self.assertFalse(transfer_tx.can_have_activity())

    def test_import_role_set_and_role_mapping_validation(self):
        setup = self.create_entity_setup()
        operating_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-ROLE-OPERATING",
            account_model=setup["income_account"],
        )
        unmapped_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-ROLE-UNMAPPED",
        )

        self.assertEqual({setup["income_account"].role}, operating_tx.get_import_role_set())
        self.assertTrue(operating_tx.is_role_mapping_valid())
        self.assertEqual(set(), unmapped_tx.get_import_role_set())
        self.assertFalse(unmapped_tx.is_role_mapping_valid())

    def test_prospect_activity_helpers_return_current_activity_or_display(self):
        setup = self.create_entity_setup()
        staged_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-ACTIVITY",
            account_model=setup["income_account"],
        )

        activity = staged_tx.get_prospect_je_activity_try(commit=True)
        staged_tx.refresh_from_db()

        self.assertEqual(activity, JournalEntryModel.OPERATING_ACTIVITY)
        self.assertEqual(staged_tx.activity, JournalEntryModel.OPERATING_ACTIVITY)
        self.assertEqual(staged_tx.get_prospect_je_activity(), JournalEntryModel.OPERATING_ACTIVITY)
        self.assertEqual(
            staged_tx.get_prospect_je_activity_display(),
            JournalEntryModel.MAP_ACTIVITIES[JournalEntryModel.OPERATING_ACTIVITY],
        )
        self.assertTrue(staged_tx.has_activity())

    def test_match_and_receipt_presence_helpers_are_state_based(self):
        setup = self.create_entity_setup()
        staged_tx = self.create_staged_transaction(
            setup,
            fit_id="FIT-STATE",
            receipt_type=ReceiptModel.TRANSFER_RECEIPT,
            activity=JournalEntryModel.OPERATING_ACTIVITY,
        )

        self.assertTrue(staged_tx.has_receipt())
        self.assertFalse(staged_tx.has_match())
        self.assertEqual(staged_tx.matches_found(), 0)
        self.assertTrue(staged_tx.is_cash_transaction())
        self.assertFalse(staged_tx.has_match_candidates())
