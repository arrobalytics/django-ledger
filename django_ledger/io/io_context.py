"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

from django.core.exceptions import ValidationError

from django_ledger.models.utils import lazy_loader


class IODigestValidationError(ValidationError):
    pass


class IODigestContextManager:

    def __init__(self, io_state: defaultdict):
        self.IO_DATA: Dict = io_state
        self.IO_RESULT = io_state['io_result']
        self.IO_MODEL = io_state['io_model']
        self.STRFTIME_FORMAT = '%B %d, %Y'

    def get_io_data(self) -> Dict:
        return self.IO_DATA

    def get_io_result(self):
        return self.IO_RESULT

    def get_io_txs_queryset(self):
        return self.IO_RESULT.txs_queryset

    def get_strftime_format(self):
        return self.STRFTIME_FORMAT

    @property
    def from_datetime(self):
        return self.get_from_datetime()

    def get_from_datetime(self, as_str: bool = False, fmt=None) -> Optional[datetime]:
        from_date = self.IO_DATA['from_date']
        if from_date:
            if as_str:
                if not fmt:
                    fmt = self.get_strftime_format()
                return from_date.strftime(fmt)
            return from_date

    @property
    def to_datetime(self):
        return self.get_to_datetime()

    def get_to_datetime(self, as_str: bool = False, fmt=None) -> datetime:
        if as_str:
            if not fmt:
                fmt = self.get_strftime_format()
            return self.IO_DATA['to_date'].strftime(fmt)
        return self.IO_DATA['to_date']

    def is_entity_model(self) -> bool:
        return isinstance(
            self.IO_MODEL,
            lazy_loader.get_entity_model()
        )

    def is_ledger_model(self) -> bool:
        return isinstance(
            self.IO_MODEL,
            lazy_loader.get_ledger_model()
        )

    def is_unit_model(self) -> bool:
        return isinstance(
            self.IO_MODEL,
            lazy_loader.get_entity_unit_model()
        )

    def is_by_unit(self) -> bool:
        return self.IO_DATA['by_unit']

    def is_by_period(self) -> bool:
        return self.IO_DATA['by_period']

    def is_by_activity(self) -> bool:
        return self.IO_DATA['by_activity']

    # Account Information
    def get_account_data(self, key_func=None) -> Dict:
        if key_func:
            return {
                key_func(acc): acc for acc in self.IO_DATA['accounts']
            }
        return {
            acc['account_uuid']: acc for acc in self.IO_DATA['accounts']
        }

    # Balance Sheet Data...
    def has_balance_sheet(self) -> bool:
        return 'balance_sheet' in self.IO_DATA

    def get_balance_sheet_data(self, raise_exception: bool = True) -> Dict:
        try:
            return self.IO_DATA['balance_sheet']
        except KeyError:
            if raise_exception:
                raise IODigestValidationError(
                    'IO Digest does not have balance sheet information available.'
                )

    # Income Statement Data...
    def has_income_statement(self) -> bool:
        return 'income_statement' in self.IO_DATA

    def get_income_statement_data(self, raise_exception: bool = True) -> Dict:
        try:
            return self.IO_DATA['income_statement']
        except KeyError:
            if raise_exception:
                raise IODigestValidationError(
                    'IO Digest does not have income statement information available.'
                )

    # Cash Flow Statement Data...
    def has_cash_flow_statement(self):
        return 'cash_flow_statement' in self.IO_DATA

    def get_cash_flow_statement_data(self, raise_exception: bool = True) -> Dict:
        try:
            return self.IO_DATA['cash_flow_statement']
        except KeyError:
            if raise_exception:
                raise IODigestValidationError(
                    'IO Digest does not have cash flow statement information available.'
                )

    # All Available Statements
    def get_financial_statements_data(self) -> Dict:
        return {
            'balance_sheet': self.get_balance_sheet_data() if self.has_balance_sheet() else None,
            'income_statement': self.get_income_statement_data() if self.has_income_statement() else None,
            'cash_flow_statement': self.get_cash_flow_statement_data() if self.has_cash_flow_statement() else None,
        }

    # CLOSING ENTRIES...

    def get_closing_entry_data(self):
        io_data = self.get_io_data()
        return io_data['accounts']
