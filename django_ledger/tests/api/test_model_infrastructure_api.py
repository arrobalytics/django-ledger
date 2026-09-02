"""
Smoke-level API tests for Django Ledger model infrastructure helpers.
"""

from django.test import SimpleTestCase

from django_ledger.models.accounts import AccountModel
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.bill import BillModel
from django_ledger.models.chart_of_accounts import ChartOfAccountModel
from django_ledger.models.closing_entry import ClosingEntryModel, ClosingEntryTransactionModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.data_import import StagedTransactionModel
from django_ledger.models.entity import EntityModel, EntityStateModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.items import ItemModel, ItemTransactionModel, UnitOfMeasureModel
from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.models.purchase_order import PurchaseOrderModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.schemas import (
    SCHEMA_DIGEST,
    SCHEMA_NET_PAYABLES,
    SCHEMA_NET_RECEIVABLE,
    SCHEMA_PNL,
)
from django_ledger.models.transactions import TransactionModel
from django_ledger.models.unit import EntityUnitModel
from django_ledger.models.utils import lazy_loader
from django_ledger.models.vendor import VendorModel
from django_ledger.report.balance_sheet import BalanceSheetReport
from django_ledger.report.cash_flow_statement import CashFlowStatementReport
from django_ledger.report.income_statement import IncomeStatementReport


class ModelInfrastructureAPITest(SimpleTestCase):
    def test_lazy_loader_resolves_public_model_classes(self):
        loader_cases = (
            (lazy_loader.get_entity_model, EntityModel),
            (lazy_loader.get_entity_unit_model, EntityUnitModel),
            (lazy_loader.get_entity_state_model, EntityStateModel),
            (lazy_loader.get_bank_account_model, BankAccountModel),
            (lazy_loader.get_account_model, AccountModel),
            (lazy_loader.get_coa_model, ChartOfAccountModel),
            (lazy_loader.get_txs_model, TransactionModel),
            (lazy_loader.get_staged_txs_model, StagedTransactionModel),
            (lazy_loader.get_purchase_order_model, PurchaseOrderModel),
            (lazy_loader.get_ledger_model, LedgerModel),
            (lazy_loader.get_journal_entry_model, JournalEntryModel),
            (lazy_loader.get_item_model, ItemModel),
            (lazy_loader.get_item_transaction_model, ItemTransactionModel),
            (lazy_loader.get_receipt_model, ReceiptModel),
            (lazy_loader.get_customer_model, CustomerModel),
            (lazy_loader.get_bill_model, BillModel),
            (lazy_loader.get_invoice_model, InvoiceModel),
            (lazy_loader.get_uom_model, UnitOfMeasureModel),
            (lazy_loader.get_vendor_model, VendorModel),
            (lazy_loader.get_estimate_model, EstimateModel),
            (lazy_loader.get_closing_entry_model, ClosingEntryModel),
            (lazy_loader.get_closing_entry_transaction_model, ClosingEntryTransactionModel),
        )

        for getter, expected_model_class in loader_cases:
            with self.subTest(getter=getter.__name__):
                self.assertIs(getter(), expected_model_class)

    def test_lazy_loader_resolves_report_classes(self):
        report_cases = (
            (lazy_loader.get_balance_sheet_report_class, BalanceSheetReport),
            (lazy_loader.get_income_statement_report_class, IncomeStatementReport),
            (lazy_loader.get_cash_flow_statement_report_class, CashFlowStatementReport),
        )

        for getter, expected_report_class in report_cases:
            with self.subTest(getter=getter.__name__):
                self.assertIs(getter(), expected_report_class)

    def test_public_schema_constants_expose_stable_top_level_shape(self):
        schema_cases = (
            (
                SCHEMA_DIGEST,
                {
                    "accounts",
                    "role_account",
                    "role_balance",
                    "group_account",
                    "group_balance",
                },
            ),
            (SCHEMA_PNL, {"entity_slug", "entity_name", "pnl_data"}),
            (SCHEMA_NET_PAYABLES, {"entity_slug", "entity_name", "net_payable_data"}),
            (SCHEMA_NET_RECEIVABLE, {"entity_slug", "entity_name", "net_receivable_data"}),
        )

        for schema, expected_property_keys in schema_cases:
            with self.subTest(schema=schema):
                self.assertIsInstance(schema, dict)
                self.assertEqual(schema["type"], "object")
                self.assertIsInstance(schema["properties"], dict)
                self.assertTrue(expected_property_keys.issubset(schema["properties"].keys()))
