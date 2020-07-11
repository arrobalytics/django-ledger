from typing import List

from ofxtools import OFXTree
from ofxtools.models.bank import STMTRS
from ofxtools.models.ofx import OFX


class OFXFileManager:

    def __init__(self, ofx_file_or_path, parse_on_load: bool = True):
        self.FILE = ofx_file_or_path
        self.ofx_tree: OFXTree = OFXTree()
        self.ofx_data: OFX or None = None
        self.statements: List[STMTRS] or None = None
        self.NUMBER_OF_STATEMENTS: int or None = None

        if parse_on_load:
            self.parse_ofx()

    def parse_ofx(self):
        self.ofx_tree.parse(self.FILE)
        self.ofx_data = self.ofx_tree.convert()
        self.statements = self.ofx_data.statements
        self.NUMBER_OF_STATEMENTS = len(self.statements)

    def get_accounts_info(self):
        return [
            {
                'bank': self.ofx_data.org,
                'fid': self.ofx_data.fid,
                'account_type': acc.accttype,
                'account_number': acc.acctid,
                'routing_number': acc.bankid,
            } for acc in self.statements
        ]
