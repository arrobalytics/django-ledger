import os
from decimal import Decimal

from django_ledger.io.ofx import OFXFileManager
from django_ledger.tests.base import DjangoLedgerBaseTest


class SimpleOFXTest(DjangoLedgerBaseTest):
    BASE_PATH = "django_ledger/tests/test_io_ofx/samples/"

    def get_sample_ofx(self, ofx_sample_name: str):
        ofx = OFXFileManager(ofx_file_or_path=os.path.join(self.BASE_PATH, ofx_sample_name))

        return ofx

    def test_ofx_v1_with_intu_bid_field(self):
        """
        OFX v1 with <INTU.BID> field. These are ofx files that are exported for Quickbooks.
        This field can be used to identify the bank in the absence of the <FI.ORG> fields.
        """
        ofx = self.get_sample_ofx("v1_with_intu_bid.ofx")
        accounts = ofx.get_accounts()

        # The bank and fid fields are not provided in this ofx file.
        self.assertIsNone(accounts[0]["fid"])
        self.assertIsNone(accounts[0]["bank"])
        # balance observed from the ofx file
        self.assertEqual(ofx.ofx_data.statements[0].balance.balamt, Decimal("123456.49"))

    def test_ofx_v1_with_open_tags(self):
        """
        OFX v1 with open tags like `<DTSERVER>20211015063225[-5:EST]` instead of `<DTSERVER>20230510120000</DTSERVER>`
        """
        ofx = self.get_sample_ofx("v1_with_open_tags.ofx")
        accounts = ofx.get_accounts()
        account = accounts[0]

        self.assertIsNone(account["fid"])
        self.assertIsNone(account["bank"])
        self.assertEqual(ofx.ofx_data.statements[0].balance.balamt, Decimal("1868.27"))

    def test_ofx_v2_good(self):
        """
        ofx v2 uses XML rather than SGML. This is a good ofx v2 file.
        """
        ofx = self.get_sample_ofx("v2_good.ofx")
        accounts = ofx.get_accounts()
        account = accounts[0]

        self.assertEqual(account["fid"], "123456789")
        self.assertEqual(account["bank"], "BANK NAME")
        self.assertEqual(ofx.ofx_data.statements[0].balance.balamt, Decimal("5000.00"))
