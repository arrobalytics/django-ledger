from django.test import TestCase

from django_ledger.io import roles
from django_ledger.models.coa_default import build_chart_of_accounts_root_map, get_default_coa
from django_ledger.regional.registry import clear_country_plugin_cache, get_country_plugin
from django_ledger_countries.settings import clear_settings_cache, get_country_code, get_ledger_setting


class RegionalInfrastructureTests(TestCase):

    def tearDown(self):
        clear_country_plugin_cache()
        clear_settings_cache()

    def test_default_country_is_us(self):
        self.assertEqual(get_country_code(), 'us')
        self.assertEqual(get_country_plugin().code, 'us')
        self.assertEqual(get_ledger_setting('CURRENCY_SYMBOL'), '$')
        self.assertFalse(get_ledger_setting('REQUIRE_SUPPORTING_DOCUMENT_ON_POST'))

    def test_build_coa_root_map_helper(self):
        sample = [
            {
                'code': '1010',
                'role': roles.ASSET_CA_CASH,
                'balance_type': 'debit',
                'name': 'Cash',
                'parent': None,
            },
        ]
        root_map = build_chart_of_accounts_root_map(sample)
        self.assertIn('root_assets', root_map)
        self.assertEqual(len(root_map['root_assets']), 1)

    def test_us_default_coa_unchanged_without_country(self):
        coa = get_default_coa()
        self.assertGreater(len(coa), 50)
