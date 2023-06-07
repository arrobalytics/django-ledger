from collections import defaultdict
from datetime import date
from typing import Dict

from django.core.exceptions import ValidationError

from django_ledger.models.utils import lazy_loader


class IODigestValidationError(ValidationError):
    pass


class IODigest:

    def __init__(self, io_data: defaultdict):
        self.IO_DATA: defaultdict = io_data
        self.IO_MODEL = self.IO_DATA['io_model']
        self.TXS_QS = self.IO_DATA['txs_qs']

    def get_from_date(self) -> date:
        return self.IO_DATA['from_date']

    def get_to_date(self) -> date:
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
            lazy_loader.get_unit_model()
        )

    # Balance Sheet...
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

    # Income Statement...
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
