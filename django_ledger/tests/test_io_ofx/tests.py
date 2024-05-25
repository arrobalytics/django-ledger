from datetime import timedelta, datetime
from random import randint
from zoneinfo import ZoneInfo

from django.conf import settings

from django_ledger.io.io_core import IOValidationError
from django_ledger.models import EntityModel
from django_ledger.tests.base import DjangoLedgerBaseTest
from django_ledger.io.ofx import OFXFileManager

import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

import pprint

def pretty_print_et(et):
    rough_string = ET.tostring(et, 'utf-8')
    reparsed = parseString(rough_string)
    return reparsed.toprettyxml(indent="\t")

class DumbOFXTest(DjangoLedgerBaseTest):

    def do_ofx_test(self, ofx_file_path: str):
        entity_model = self.get_random_entity_model()

        ofx = OFXFileManager(ofx_file_or_path=ofx_file_path)

        pprint.pprint(ofx.ofx_tree)

        print("")

        pprint.pprint(ofx.ofx_data)

        accts = ofx.get_accounts()

        self.assertEqual(True, True)

        for acct in accts:
            print(acct["account_number"])

        return accts

    def test_good1(self):
        accts = self.do_ofx_test("django_ledger/tests/test_io_ofx/samples/v2_good.ofx")

        self.assertIsNotNone(accts[0]["fid"])
        self.assertIsNotNone(accts[0]["bank"])


    def test_intu_bid(self):
        accts = self.do_ofx_test("django_ledger/tests/test_io_ofx/samples/v1_with_intu_bid.ofx")

        self.assertIsNone(accts[0]["fid"])
        self.assertIsNone(accts[0]["bank"])


    def test_open_tags(self):
        accts = self.do_ofx_test("django_ledger/tests/test_io_ofx/samples/v1_with_open_tags.ofx")

        self.assertIsNone(accts[0]["fid"])
        self.assertIsNone(accts[0]["bank"])
