from django.test import TestCase, override_settings

from django_ledger.models.coa_default import build_chart_of_accounts_root_map
from django_ledger.regional.registry import clear_country_plugin_cache, get_country_plugin
from django_ledger_countries.de.coa import skr03
from django_ledger_countries.settings import clear_settings_cache, get_country_code, get_ledger_setting

class GermanyRegionalTests(TestCase):

    def tearDown(self):
        clear_country_plugin_cache()
        clear_settings_cache()

    @override_settings(DJANGO_LEDGER_COUNTRY='de')
    def test_germany_country_plugin(self):
        clear_country_plugin_cache()
        clear_settings_cache()
        self.assertEqual(get_country_code(), 'de')
        self.assertEqual(get_country_plugin().code, 'de')
        self.assertEqual(get_ledger_setting('CURRENCY_SYMBOL'), '€')
        self.assertTrue(get_ledger_setting('REQUIRE_SUPPORTING_DOCUMENT_ON_POST'))
        self.assertEqual(get_ledger_setting('DEFAULT_COA'), 'skr03')

    @override_settings(DJANGO_LEDGER_COUNTRY='de')
    def test_skr03_root_map(self):
        clear_country_plugin_cache()
        clear_settings_cache()
        from django_ledger_countries.de.coa import skr03

        skr03.clear_datev_coa_cache()
        root_map = build_chart_of_accounts_root_map(skr03.get_skr03_accounts())
        self.assertTrue(root_map)
        self.assertGreater(len(root_map.keys()), 0)

    @override_settings(DJANGO_LEDGER_COUNTRY='de')
    def test_skr03_account_translations(self):
        clear_country_plugin_cache()
        clear_settings_cache()
        from django_ledger_countries.de.coa import skr03

        skr03.clear_datev_coa_cache()
        translations = skr03.get_account_translations()
        self.assertGreater(len(translations), 4000)
        locales = {entry['locale'] for entry in translations}
        self.assertIn('de', locales)
        self.assertIn('en', locales)
