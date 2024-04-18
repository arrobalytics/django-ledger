"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""

from django.apps import apps


class LazyLoader:
    """
    A class that provides lazy-loading functionality for various models in the django_ledger app.

    Attributes:
        app_config (AppConfig): The AppConfig object for the django_ledger app.

        ENTITY_MODEL (str): The name of the entity model.
        LEDGER_MODEL (str): The name of the ledger model.
        JE_MODEL (str): The name of the journal entry model.
        TRANSACTION_MODEL (str): The name of the transaction model.
        ACCOUNT_MODEL (str): The name of the account model.
        COA_MODEL (str): The name of the chart of account model.

        ENTITY_STATE_MODEL (str): The name of the entity state model.
        ENTITY_UNIT_MODEL (str): The name of the entity unit model.
        CLOSING_ENTRY_MODEL (str): The name of the closing entry model.
        CLOSING_ENTRY_TRANSACTION_MODEL (str): The name of the closing entry transaction model.

        BANK_ACCOUNT_MODEL (str): The name of the bank account model.
        PURCHASE_ORDER_MODEL (str): The name of the purchase order model.

        CUSTOMER_MODEL (str): The name of the customer model.
        INVOICE_MODEL (str): The name of the invoice model.
        BILL_MODEL (str): The name of the bill model.
        UOM_MODEL (str): The name of the unit of measure model.
        VENDOR_MODEL (str): The name of the vendor model.
        ESTIMATE_MODEL (str): The name of the estimate model.
        ITEM_MODEL (str): The name of the item model.
        ITEM_TRANSACTION_MODEL (str): The name of the item transaction model.

        ENTITY_DATA_GENERATOR (EntityDataGenerator): The EntityDataGenerator class used for generating entity data.
        BALANCE_SHEET_REPORT_CLASS (BalanceSheetReport): The BalanceSheetReport class used for generating balance sheet reports.
        INCOME_STATEMENT_REPORT_CLASS (IncomeStatementReport): The IncomeStatementReport class used for generating income statement reports.
        CASH_FLOW_STATEMENT_REPORT_CLASS (CashFlowStatementReport): The CashFlowStatementReport class used for generating cash flow statement reports.

    Methods:
        get_entity_model() -> Model: Returns the entity model.
        get_entity_unit_model() -> Model: Returns the entity unit model.
        get_entity_state_model() -> Model: Returns the entity state model.
        get_bank_account_model() -> Model: Returns the bank account model.
        get_account_model() -> Model: Returns the account model.
        get_coa_model() -> Model: Returns the chart of account model.
        get_txs_model() -> Model: Returns the transaction model.
        get_purchase_order_model() -> Model: Returns the purchase order model.
        get_ledger_model() -> Model: Returns the ledger model.
        get_journal_entry_model() -> Model: Returns the journal entry model.
        get_item_model() -> Model: Returns the item model.
        get_item_transaction_model() -> Model: Returns the item transaction model.
        get_customer_model() -> Model: Returns the customer model.
        get_bill_model() -> Model: Returns the bill model.
        get_invoice_model() -> Model: Returns the invoice model.
        get_uom_model() -> Model: Returns the unit of measure model.
        get_vendor_model() -> Model: Returns the vendor model.
        get_estimate_model() -> Model: Returns the estimate model.
        get_closing_entry_model() -> Model: Returns the closing entry model.
        get_closing_entry_transaction_model() -> Model: Returns the closing entry transaction model.
        get_entity_data_generator() -> EntityDataGenerator: Returns the EntityDataGenerator class.
        get_balance_sheet_report_class() -> BalanceSheetReport: Returns the BalanceSheetReport class.
        get_income_statement_report_class() -> IncomeStatementReport: Returns the IncomeStatementReport class.
        get_cash_flow_statement_report_class() -> CashFlowStatementReport: Returns the CashFlowStatementReport class.
    """

    app_config = apps.get_app_config(app_label='django_ledger')

    ENTITY_MODEL = 'entitymodel'
    LEDGER_MODEL = 'ledgermodel'
    JE_MODEL = 'journalentrymodel'
    TRANSACTION_MODEL = 'transactionmodel'
    ACCOUNT_MODEL = 'accountmodel'
    COA_MODEL = 'chartofaccountmodel'

    ENTITY_STATE_MODEL = 'entitystatemodel'
    ENTITY_UNIT_MODEL = 'entityunitmodel'
    CLOSING_ENTRY_MODEL = 'closingentrymodel'
    CLOSING_ENTRY_TRANSACTION_MODEL = 'closingentrytransactionmodel'

    BANK_ACCOUNT_MODEL = 'bankaccountmodel'
    PURCHASE_ORDER_MODEL = 'purchaseordermodel'

    CUSTOMER_MODEL = 'customermodel'
    INVOICE_MODEL = 'invoicemodel'
    BILL_MODEL = 'billmodel'
    UOM_MODEL = 'unitofmeasuremodel'
    VENDOR_MODEL = 'vendormodel'
    ESTIMATE_MODEL = 'estimatemodel'
    ITEM_MODEL = 'itemmodel'
    ITEM_TRANSACTION_MODEL = 'itemtransactionmodel'

    ENTITY_DATA_GENERATOR = None
    BALANCE_SHEET_REPORT_CLASS = None
    INCOME_STATEMENT_REPORT_CLASS = None
    CASH_FLOW_STATEMENT_REPORT_CLASS = None



    def get_entity_model(self):
        return self.app_config.get_model(self.ENTITY_MODEL)

    def get_entity_unit_model(self):
        return self.app_config.get_model(self.ENTITY_UNIT_MODEL)

    def get_entity_state_model(self):
        return self.app_config.get_model(self.ENTITY_STATE_MODEL)

    def get_bank_account_model(self):
        return self.app_config.get_model(self.BANK_ACCOUNT_MODEL)

    def get_account_model(self):
        return self.app_config.get_model(self.ACCOUNT_MODEL)

    def get_coa_model(self):
        return self.app_config.get_model(self.COA_MODEL)

    def get_txs_model(self):
        return self.app_config.get_model(self.TRANSACTION_MODEL)

    def get_purchase_order_model(self):
        return self.app_config.get_model(self.PURCHASE_ORDER_MODEL)

    def get_ledger_model(self):
        self.get_entity_unit_model()
        return self.app_config.get_model(self.LEDGER_MODEL)

    def get_journal_entry_model(self):
        return self.app_config.get_model(self.JE_MODEL)

    def get_item_model(self):
        return self.app_config.get_model(self.ITEM_MODEL)

    def get_item_transaction_model(self):
        return self.app_config.get_model(self.ITEM_TRANSACTION_MODEL)

    def get_customer_model(self):
        return self.app_config.get_model(self.CUSTOMER_MODEL)

    def get_bill_model(self):
        return self.app_config.get_model(self.BILL_MODEL)

    def get_invoice_model(self):
        return self.app_config.get_model(self.INVOICE_MODEL)

    def get_uom_model(self):
        return self.app_config.get_model(self.UOM_MODEL)

    def get_vendor_model(self):
        return self.app_config.get_model(self.VENDOR_MODEL)

    def get_estimate_model(self):
        return self.app_config.get_model(self.ESTIMATE_MODEL)

    def get_closing_entry_model(self):
        return self.app_config.get_model(self.CLOSING_ENTRY_MODEL)

    def get_closing_entry_transaction_model(self):
        return self.app_config.get_model(self.CLOSING_ENTRY_TRANSACTION_MODEL)

    def get_entity_data_generator(self):
        if not self.ENTITY_DATA_GENERATOR:
            from django_ledger.io.io_generator import EntityDataGenerator
            self.ENTITY_DATA_GENERATOR = EntityDataGenerator
        return self.ENTITY_DATA_GENERATOR

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
