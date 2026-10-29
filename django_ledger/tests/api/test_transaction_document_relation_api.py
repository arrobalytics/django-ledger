"""
High-level API behavior tests for TransactionModel document relation filters.

These tests use draft document wrapper ledgers only; they do not exercise bill
or invoice lifecycle behavior.
"""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import BillModel, InvoiceModel, JournalEntryModel, TransactionModel
from django_ledger.models.entity import EntityModel


class TransactionDocumentRelationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_tx_document_relation_admin",
            email="api-tx-document-relation-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_setup(self, *, name="API Transaction Document Relation Entity"):
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
            is_role_default=True,
        )
        prepaid_account = coa_model.create_account(
            code="1310",
            name=f"{name} Prepaid",
            role="asset_ca_prepaid",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        payable_account = coa_model.create_account(
            code="2010",
            name=f"{name} Accounts Payable",
            role="lia_cl_acc_payable",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        receivable_account = coa_model.create_account(
            code="1210",
            name=f"{name} Receivable",
            role="asset_ca_recv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        deferred_revenue_account = coa_model.create_account(
            code="2310",
            name=f"{name} Deferred Revenue",
            role="lia_cl_def_rev",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        customer_model = entity_model.create_customer(
            {
                "customer_name": f"{name} Customer",
                "description": f"{name} customer",
                "active": True,
                "hidden": False,
            },
            commit=True,
        )
        vendor_model = entity_model.create_vendor(
            {
                "vendor_name": f"{name} Vendor",
                "description": f"{name} vendor",
                "active": True,
                "hidden": False,
            },
            commit=True,
        )

        return {
            "cash_account": cash_account,
            "customer_model": customer_model,
            "deferred_revenue_account": deferred_revenue_account,
            "entity_model": entity_model,
            "payable_account": payable_account,
            "prepaid_account": prepaid_account,
            "receivable_account": receivable_account,
            "vendor_model": vendor_model,
        }

    def create_bill(self, setup, *, suffix):
        return setup["entity_model"].create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_NET_30,
            date_draft=date(2026, 1, 15),
            ledger_name=f"API TX Bill Relation Ledger {suffix}",
            commit=True,
        )

    def create_invoice(self, setup, *, suffix):
        return setup["entity_model"].create_invoice(
            customer_model=setup["customer_model"],
            terms=InvoiceModel.TERMS_NET_30,
            date_draft=date(2026, 1, 15),
            ledger_name=f"API TX Invoice Relation Ledger {suffix}",
            commit=True,
        )

    def create_transaction_for_document(self, document_model, *, account, description):
        journal_entry = JournalEntryModel.objects.create(
            ledger=document_model.ledger,
            timestamp=self.make_timestamp(),
            description=f"{description} Journal Entry",
        )
        return TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("10.00"),
            description=description,
        )

    def transaction_ids(self, queryset):
        return set(queryset.values_list("uuid", flat=True))

    def test_for_bill_filters_by_bill_model_uuid_and_uuid_string(self):
        setup = self.create_entity_setup(name="API TX Bill Relation Entity")
        bill_a = self.create_bill(setup, suffix="A")
        bill_b = self.create_bill(setup, suffix="B")
        bill_a_tx = self.create_transaction_for_document(
            bill_a,
            account=setup["prepaid_account"],
            description="API TX Bill Relation A",
        )
        bill_b_tx = self.create_transaction_for_document(
            bill_b,
            account=setup["prepaid_account"],
            description="API TX Bill Relation B",
        )
        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"])

        for bill_lookup in (bill_a, bill_a.uuid, str(bill_a.uuid)):
            with self.subTest(bill_lookup=bill_lookup):
                bill_qs = transaction_qs.for_bill(bill_lookup)

                self.assertEqual({bill_a_tx.uuid}, self.transaction_ids(bill_qs))
                self.assertNotIn(bill_b_tx.uuid, self.transaction_ids(bill_qs))

    def test_for_invoice_filters_by_invoice_model_uuid_and_uuid_string(self):
        setup = self.create_entity_setup(name="API TX Invoice Relation Entity")
        invoice_a = self.create_invoice(setup, suffix="A")
        invoice_b = self.create_invoice(setup, suffix="B")
        invoice_a_tx = self.create_transaction_for_document(
            invoice_a,
            account=setup["receivable_account"],
            description="API TX Invoice Relation A",
        )
        invoice_b_tx = self.create_transaction_for_document(
            invoice_b,
            account=setup["receivable_account"],
            description="API TX Invoice Relation B",
        )
        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"])

        for invoice_lookup in (invoice_a, invoice_a.uuid, str(invoice_a.uuid)):
            with self.subTest(invoice_lookup=invoice_lookup):
                invoice_qs = transaction_qs.for_invoice(invoice_lookup)

                self.assertEqual({invoice_a_tx.uuid}, self.transaction_ids(invoice_qs))
                self.assertNotIn(invoice_b_tx.uuid, self.transaction_ids(invoice_qs))
