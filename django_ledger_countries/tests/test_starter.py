import csv
from pathlib import Path

from django.test import TestCase

from django_ledger_countries.de.coa.starter import (
    DEFAULT_SCHOOL_STARTER_CODES,
    get_starter_account_codes,
)


class StarterActivationTests(TestCase):

    def test_default_starter_covers_bildungsurlaub_basics(self):
        codes = get_starter_account_codes()
        self.assertGreaterEqual(len(codes), 25)
        self.assertLessEqual(len(codes), 40)
        self.assertIn('1200 00', codes)
        self.assertIn('8100 00', codes)
        self.assertIn('3100 11', codes)
        self.assertIn('4210 10', codes)
        self.assertIn('4955 00', codes)

    def test_starter_codes_exist_in_default_tuple(self):
        self.assertEqual(tuple(sorted(get_starter_account_codes())), tuple(sorted(DEFAULT_SCHOOL_STARTER_CODES)))

    def test_all_default_starter_codes_exist_in_datev_csv(self):
        path = Path(__file__).resolve().parents[1] / 'de' / 'coa' / 'skr03' / '2026_Schulen_freie_Träger.csv'
        postable = set()
        with path.open(encoding='utf-8') as handle:
            for row in csv.DictReader(handle):
                if row.get('is_postable') == 'true' and row.get('is_range') != 'true':
                    postable.add(row['account_number'].strip())
        missing = sorted(set(DEFAULT_SCHOOL_STARTER_CODES) - postable)
        self.assertEqual(missing, [])
