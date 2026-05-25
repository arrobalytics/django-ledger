from django.test import SimpleTestCase, override_settings

from django.core.exceptions import ValidationError

from django_ledger_countries.de.coa.datev_loader import (
    load_datev_coa_rows,
    map_skr03_account,
    resolve_csv_path,
)
from django_ledger_countries.de.validators import validate_datev_account_code
from django_ledger.io import roles
from django_ledger.io.roles import CREDIT, DEBIT
from django_ledger_countries.de.roles import ASSET_CA_VAT_RECEIVABLE, LIABILITY_CL_VAT_PAYABLE


class DatevValidatorTests(SimpleTestCase):

    def test_valid_datev_code(self):
        validate_datev_account_code('1200 00')
        validate_datev_account_code('8400 10')

    def test_invalid_datev_code(self):
        with self.assertRaises(ValidationError):
            validate_datev_account_code('120000')
        with self.assertRaises(ValidationError):
            validate_datev_account_code('1200-00')


class DatevMappingTests(SimpleTestCase):

    def test_maps_bank_and_vat_accounts(self):
        role, balance = map_skr03_account('1', '1200 00', 'Bank')
        self.assertEqual(role, roles.ASSET_CA_CASH)
        self.assertEqual(balance, DEBIT)

        role, balance = map_skr03_account('1', '1576 00', 'Abziehbare Vorsteuer 19 %')
        self.assertEqual(role, ASSET_CA_VAT_RECEIVABLE)
        self.assertEqual(balance, DEBIT)

        role, balance = map_skr03_account('1', '1776 00', 'Umsatzsteuer 19 %')
        self.assertEqual(role, LIABILITY_CL_VAT_PAYABLE)
        self.assertEqual(balance, CREDIT)

    def test_maps_revenue_and_expense_classes(self):
        role, balance = map_skr03_account('8', '8000 00', 'Umsatzerlöse')
        self.assertEqual(role, roles.INCOME_OPERATIONAL)
        self.assertEqual(balance, CREDIT)

        role, balance = map_skr03_account('4', '4100 00', 'Löhne und Gehälter')
        self.assertEqual(role, roles.EXPENSE_OPERATIONAL)
        self.assertEqual(balance, DEBIT)


class DatevCsvLoaderTests(SimpleTestCase):

    def test_loads_postable_accounts_from_package_csv(self):
        path = resolve_csv_path()
        self.assertTrue(path.exists(), msg=f'Missing CSV fixture: {path}')
        rows = load_datev_coa_rows(path)
        self.assertGreater(len(rows), 2000)
        self.assertEqual(rows[0]['code'], '0005 00')
        self.assertIn(' ', rows[0]['code'])
        self.assertEqual(rows[0]['balance_type'], DEBIT)

    @override_settings(DJANGO_LEDGER_COUNTRY='de')
    def test_skr03_accounts_keep_datev_codes(self):
        from django_ledger.regional.registry import clear_country_plugin_cache
        from django_ledger_countries.settings import clear_settings_cache
        from django_ledger_countries.de.coa import skr03
        from django_ledger_countries.de.coa.starter import get_starter_account_codes

        clear_country_plugin_cache()
        clear_settings_cache()
        skr03.clear_datev_coa_cache()
        accounts = skr03.get_skr03_accounts()
        self.assertGreater(len(accounts), 2000)
        self.assertTrue(all(' ' in account['code'] for account in accounts[:10]))
        active = [a for a in accounts if a.get('active')]
        self.assertEqual(len(active), len(get_starter_account_codes()))
