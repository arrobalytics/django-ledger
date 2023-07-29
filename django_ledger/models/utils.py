"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""


class LazyLoader:
    """
    This class eliminates the circle dependency between models.
    """
    ENTITY_MODEL = None
    ENTITY_STATE_MODEL = None
    UNIT_MODEL = None
    ACCOUNT_MODEL = None
    BANK_ACCOUNT_MODEL = None
    LEDGER_MODEL = None
    TXS_MODEL = None
    JE_MODEL = None
    ITEM_MODEL = None
    ITEM_TRANSACTION_MODEL = None
    CUSTOMER_MODEL = None
    INVOICE_MODEL = None
    BILL_MODEL = None
    UOM_MODEL = None
    VENDOR_MODEL = None
    TRANSACTION_MODEL = None
    ENTITY_UNIT_MODEL = None
    PURCHASE_ORDER_MODEL = None
    ESTIMATE_MODEL = None
    CLOSING_ENTRY_MODEL = None

    ENTITY_DATA_GENERATOR = None

    BALANCE_SHEET_REPORT_CLASS = None
    INCOME_STATEMENT_REPORT_CLASS = None
    CASH_FLOW_STATEMENT_REPORT_CLASS = None

    def get_entity_model(self):
        if not self.ENTITY_MODEL:
            from django_ledger.models import EntityModel
            self.ENTITY_MODEL = EntityModel
        return self.ENTITY_MODEL

    def get_entity_state_model(self):
        if not self.ENTITY_STATE_MODEL:
            from django_ledger.models import EntityStateModel
            self.ENTITY_STATE_MODEL = EntityStateModel
        return self.ENTITY_STATE_MODEL

    def get_bank_account_model(self):
        if not self.BANK_ACCOUNT_MODEL:
            from django_ledger.models import BankAccountModel
            self.BANK_ACCOUNT_MODEL = BankAccountModel
        return self.BANK_ACCOUNT_MODEL

    def get_account_model(self):
        if not self.ACCOUNT_MODEL:
            from django_ledger.models import AccountModel
            self.ACCOUNT_MODEL = AccountModel
        return self.ACCOUNT_MODEL

    def get_txs_model(self):
        if not self.TXS_MODEL:
            from django_ledger.models import TransactionModel
            self.TXS_MODEL = TransactionModel
        return self.TXS_MODEL

    def get_purchase_order_model(self):
        if not self.PURCHASE_ORDER_MODEL:
            from django_ledger.models import PurchaseOrderModel
            self.PURCHASE_ORDER_MODEL = PurchaseOrderModel
        return self.PURCHASE_ORDER_MODEL

    def get_ledger_model(self):
        if not self.LEDGER_MODEL:
            from django_ledger.models import LedgerModel
            self.LEDGER_MODEL = LedgerModel
        return self.LEDGER_MODEL

    def get_unit_model(self):
        if not self.UNIT_MODEL:
            from django_ledger.models import EntityUnitModel
            self.UNIT_MODEL = EntityUnitModel
        return self.UNIT_MODEL

    def get_journal_entry_model(self):
        if not self.JE_MODEL:
            from django_ledger.models import JournalEntryModel
            self.JE_MODEL = JournalEntryModel
        return self.JE_MODEL

    def get_item_model(self):
        if not self.ITEM_MODEL:
            from django_ledger.models import ItemModel
            self.ITEM_MODEL = ItemModel
        return self.ITEM_MODEL

    def get_item_transaction_model(self):
        if not self.ITEM_TRANSACTION_MODEL:
            from django_ledger.models import ItemTransactionModel
            self.ITEM_TRANSACTION_MODEL = ItemTransactionModel
        return self.ITEM_TRANSACTION_MODEL

    def get_customer_model(self):
        if not self.CUSTOMER_MODEL:
            from django_ledger.models import CustomerModel
            self.CUSTOMER_MODEL = CustomerModel
        return self.CUSTOMER_MODEL

    def get_bill_model(self):
        if not self.BILL_MODEL:
            from django_ledger.models import BillModel
            self.BILL_MODEL = BillModel
        return self.BILL_MODEL

    def get_invoice_model(self):
        if not self.INVOICE_MODEL:
            from django_ledger.models import InvoiceModel
            self.INVOICE_MODEL = InvoiceModel
        return self.INVOICE_MODEL

    def get_uom_model(self):
        if not self.UOM_MODEL:
            from django_ledger.models import UnitOfMeasureModel
            self.UOM_MODEL = UnitOfMeasureModel
        return self.UOM_MODEL

    def get_vendor_model(self):
        if not self.VENDOR_MODEL:
            from django_ledger.models import VendorModel
            self.VENDOR_MODEL = VendorModel
        return self.VENDOR_MODEL

    def get_transaction_model(self):
        if not self.TRANSACTION_MODEL:
            from django_ledger.models import TransactionModel
            self.TRANSACTION_MODEL = TransactionModel
        return self.TRANSACTION_MODEL

    def get_entity_unit_model(self):
        if not self.ENTITY_UNIT_MODEL:
            from django_ledger.models import EntityUnitModel
            self.ENTITY_UNIT_MODEL = EntityUnitModel
        return self.ENTITY_UNIT_MODEL

    def get_estimate_model(self):
        if not self.ESTIMATE_MODEL:
            from django_ledger.models import EstimateModel
            self.ESTIMATE_MODEL = EstimateModel
        return self.ESTIMATE_MODEL

    def get_entity_data_generator(self):
        if not self.ENTITY_DATA_GENERATOR:
            from django_ledger.io.data_generator import EntityDataGenerator
            self.ENTITY_DATA_GENERATOR = EntityDataGenerator
        return self.ENTITY_DATA_GENERATOR

    def get_closing_entry_model(self):
        if not self.CLOSING_ENTRY_MODEL:
            from django_ledger.models import ClosingEntryModel
            self.CLOSING_ENTRY_MODEL = ClosingEntryModel
        return self.CLOSING_ENTRY_MODEL

    def get_balance_sheet_report_class(self):
        if not self.BALANCE_SHEET_REPORT_CLASS:
            from django_ledger.report.balance_sheet import BalanceSheetReport
            self.BALANCE_SHEET_REPORT_CLASS = BalanceSheetReport
        return self.BALANCE_SHEET_REPORT_CLASS

    def get_income_statement_report_class(self):
        if not self.INCOME_STATEMENT_REPORT_CLASS:
            from django_ledger.report.income_statement import IncomeStatementReport
            self.INCOME_STATEMENT_REPORT_CLASS = IncomeStatementReport
        return self.INCOME_STATEMENT_REPORT_CLASS

    def get_cash_flow_statement_report_class(self):
        if not self.CASH_FLOW_STATEMENT_REPORT_CLASS:
            from django_ledger.report.cash_flow_statement import CashFlowStatementReport
            self.CASH_FLOW_STATEMENT_REPORT_CLASS = CashFlowStatementReport
        return self.CASH_FLOW_STATEMENT_REPORT_CLASS


lazy_loader = LazyLoader()
