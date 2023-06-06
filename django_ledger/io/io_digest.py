from collections import defaultdict
from datetime import date
from typing import Dict

from django.core.exceptions import ValidationError

from django_ledger.models.utils import lazy_loader


class IODigestValidationError(ValidationError):
    pass


class IODigest:

    def __init__(self, io_digest: defaultdict):
        self.IO_DIGEST: defaultdict = io_digest
        self.IO_MODEL = self.IO_DIGEST['io_model']
        self.TXS_QS = self.IO_DIGEST['txs_qs']

    def get_to_date(self) -> date:
        return self.IO_DIGEST['to_date']

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
        return 'balance_sheet' in self.IO_DIGEST

    def get_balance_sheet_data(self, raise_exception: bool = True) -> Dict:
        try:
            return self.IO_DIGEST['balance_sheet']
        except KeyError:
            if raise_exception:
                raise IODigestValidationError(
                    'IO Digest does not have balance sheet information available.'
                )
