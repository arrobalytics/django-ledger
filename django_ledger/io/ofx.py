"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from typing import List, Optional, Dict

from django.core.exceptions import ValidationError
from ofxtools import OFXTree
from ofxtools.models.bank import STMTRS
from ofxtools.models.ofx import OFX


class OFXImportValidationError(ValidationError):
    pass


class OFXFileManager:

    def __init__(self, ofx_file_or_path, parse_on_load: bool = True):
        self.FILE = ofx_file_or_path
        self.ofx_tree: OFXTree = OFXTree()
        self.ofx_data: OFX or None = None
        self.statements: List[STMTRS] or None = None
        self.NUMBER_OF_STATEMENTS: int = 0

        if parse_on_load:
            self.parse_ofx()

        if self.NUMBER_OF_STATEMENTS != 1:
            raise OFXImportValidationError('Only one account per OFX file is supported.')

        self.BANK_NAME = self.ofx_data.fi.org if hasattr(self.ofx_data.fi, 'org') else None
        self.FID = self.ofx_data.fi.fid if hasattr(self.ofx_data.fi, 'fid') else None
        self.ACCOUNT_DATA: Optional[Dict] = None

        self.get_account_data()
        # self.ACCOUNT_TXS = self.get_account_txs(account=self.ACCOUNTS[0]['account'].acctid)

    def parse_ofx(self):
        self.ofx_tree.parse(self.FILE)
        self.ofx_data = self.ofx_tree.convert()
        self.statements = self.ofx_data.statements
        self.NUMBER_OF_STATEMENTS = len(self.statements)

    def statement_attrs(self):
        return [a for a in dir(self.statements[0]) if a[0] != '_']

    def get_account_data(self):
        if self.ACCOUNT_DATA is None:
            self.ACCOUNT_DATA = [
                dict(
                    (attr, getattr(account, attr)) for attr in self.statement_attrs()
                ) | {
                    'bank': self.BANK_NAME,
                    'fid': self.FID
                } for account in self.statements
            ][0]
        return self.ACCOUNT_DATA

    def get_account_number(self):
        return self.get_account_data()['account'].acctid

    def get_account_txs(self):
        acc_statement = next(iter(
            st for st in self.ofx_data.statements if st.account.acctid == self.get_account_number()
        ))
        return acc_statement.banktranlist
