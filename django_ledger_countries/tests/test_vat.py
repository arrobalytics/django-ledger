from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings

from django_ledger.io import roles
from django_ledger.regional.registry import clear_country_plugin_cache
from django_ledger_extensions.models import EntityTaxProfile
from django_ledger_countries.de import vat as vat_module
from django_ledger_countries.de.vat.accounts import (
    EXEMPT_REVENUE_CODE,
    TAXABLE_REVENUE_CODE,
    VAT_INPUT_CODE,
    VAT_OUTPUT_CODE,
    filter_starter_codes_for_regime,
)
from django_ledger_countries.de.vat.context import VatContext
from django_ledger_countries.de.vat.registry import get_vat_handler
from django_ledger_countries.de.coa.starter import get_starter_account_codes
from django_ledger_countries.settings import clear_settings_cache, get_ledger_setting


class VatSettingsTests(SimpleTestCase):

    def tearDown(self):
        clear_settings_cache()

    @override_settings(DJANGO_LEDGER_COUNTRY='de')
    def test_default_tax_regime_is_exempt(self):
        clear_settings_cache()
        self.assertEqual(get_ledger_setting('DEFAULT_TAX_REGIME'), 'exempt')

    @override_settings(
        DJANGO_LEDGER_COUNTRY='de',
        DJANGO_LEDGER_DE_DEFAULT_TAX_REGIME='small_business',
    )
    def test_default_profile_values_for_kleinunternehmer(self):
        clear_settings_cache()
        values = vat_module.get_default_tax_profile_values()
        self.assertEqual(values['tax_regime'], 'small_business')
        self.assertEqual(values['default_vat_rate'], '0')

    @override_settings(
        DJANGO_LEDGER_COUNTRY='de',
        DJANGO_LEDGER_DE_DEFAULT_TAX_REGIME='standard',
        DJANGO_LEDGER_DE_DEFAULT_VAT_RATE='0.19',
    )
    def test_default_profile_values_for_standard(self):
        clear_settings_cache()
        values = vat_module.get_default_tax_profile_values()
        self.assertEqual(values['tax_regime'], 'standard')
        self.assertEqual(values['default_vat_rate'], '0.19')


class VatStarterFilterTests(SimpleTestCase):

    def test_exempt_regime_excludes_vat_and_taxable_revenue_accounts(self):
        codes = filter_starter_codes_for_regime(get_starter_account_codes(), 'exempt')
        self.assertIn(EXEMPT_REVENUE_CODE, codes)
        self.assertNotIn(TAXABLE_REVENUE_CODE, codes)
        self.assertNotIn(VAT_INPUT_CODE, codes)
        self.assertNotIn(VAT_OUTPUT_CODE, codes)

    def test_small_business_regime_excludes_vat_and_exempt_revenue(self):
        codes = filter_starter_codes_for_regime(get_starter_account_codes(), 'small_business')
        self.assertNotIn(EXEMPT_REVENUE_CODE, codes)
        self.assertNotIn(TAXABLE_REVENUE_CODE, codes)
        self.assertNotIn(VAT_INPUT_CODE, codes)
        self.assertIn('8200 00', codes)

    def test_standard_regime_includes_vat_accounts(self):
        codes = filter_starter_codes_for_regime(get_starter_account_codes(), 'standard')
        self.assertIn(TAXABLE_REVENUE_CODE, codes)
        self.assertIn(VAT_INPUT_CODE, codes)
        self.assertNotIn(EXEMPT_REVENUE_CODE, codes)


class VatHandlerTests(SimpleTestCase):

    def test_exempt_handler_passes_transactions_through(self):
        handler = get_vat_handler('exempt')
        ctx = SimpleNamespace(vat_rate=Decimal('0'))
        txs = [SimpleNamespace(amount=Decimal('100.00'))]
        self.assertIs(handler.adjust_posting(ctx, None, txs), txs)

    def test_exempt_handler_provides_invoice_notice(self):
        handler = get_vat_handler('exempt')
        notice = handler.invoice_vat_notice(SimpleNamespace())
        self.assertIn('§ 4 UStG', notice)

    def test_small_business_handler_provides_invoice_notice(self):
        handler = get_vat_handler('small_business')
        notice = handler.invoice_vat_notice(SimpleNamespace())
        self.assertIn('§ 19 UStG', notice)


class VatAdjustPostingTests(TestCase):

    def tearDown(self):
        clear_country_plugin_cache()
        clear_settings_cache()

    @override_settings(DJANGO_LEDGER_COUNTRY='de')
    @patch('django_ledger_countries.de.vat.standard.lazy_loader')
    def test_standard_regime_splits_vat_on_income_and_expense_lines(self, lazy_loader):
        clear_settings_cache()
        account_id = uuid4()
        income_account = SimpleNamespace(uuid=account_id, role=roles.INCOME_OPERATIONAL)
        expense_id = uuid4()
        expense_account = SimpleNamespace(uuid=expense_id, role=roles.EXPENSE_OPERATIONAL)
        cash_id = uuid4()
        cash_account = SimpleNamespace(uuid=cash_id, role=roles.ASSET_CA_CASH)

        vat_input = SimpleNamespace(role='asset_ca_vat_receivable')
        vat_output = SimpleNamespace(role='liability_cl_vat_payable')
        coa = MagicMock()
        coa.accountmodel_set.filter.side_effect = [
            MagicMock(first=MagicMock(return_value=vat_input)),
            MagicMock(first=MagicMock(return_value=vat_output)),
        ]

        AccountModel = MagicMock()
        AccountModel.objects.filter.return_value = [income_account, expense_account, cash_account]
        TransactionModel = MagicMock()
        lazy_loader.get_txs_model.return_value = TransactionModel
        lazy_loader.get_account_model.return_value = AccountModel

        revenue_tx = SimpleNamespace(
            account_id=account_id,
            account=income_account,
            amount=Decimal('119.00'),
            tx_type='credit',
            journal_entry=SimpleNamespace(),
        )
        expense_tx = SimpleNamespace(
            account_id=expense_id,
            account=expense_account,
            amount=Decimal('119.00'),
            tx_type='debit',
            journal_entry=SimpleNamespace(),
        )
        cash_tx = SimpleNamespace(
            account_id=cash_id,
            account=cash_account,
            amount=Decimal('119.00'),
            tx_type='debit',
            journal_entry=SimpleNamespace(),
        )

        tax_profile = SimpleNamespace(
            tax_regime='standard',
            default_vat_rate=Decimal('0.19'),
            TaxRegime=EntityTaxProfile.TaxRegime,
        )
        entity = SimpleNamespace(default_coa=coa, tax_profile=tax_profile)
        document = SimpleNamespace(
            ledger=SimpleNamespace(entity=entity),
            get_migrate_state_desc=lambda: 'Test VAT',
        )

        ctx = VatContext(
            entity=entity,
            tax_profile=tax_profile,
            vat_rate=Decimal('0.19'),
            coa=coa,
        )
        handler = get_vat_handler('standard')
        result = handler.adjust_posting(ctx, document, [revenue_tx, expense_tx, cash_tx])

        self.assertEqual(revenue_tx.amount, Decimal('100.00'))
        self.assertEqual(expense_tx.amount, Decimal('100.00'))
        self.assertEqual(cash_tx.amount, Decimal('119.00'))
        self.assertEqual(len(result), 5)


class EntityTaxProfileValidationTests(TestCase):

    def test_standard_regime_requires_positive_vat_rate(self):
        profile = EntityTaxProfile(
            tax_regime=EntityTaxProfile.TaxRegime.STANDARD,
            default_vat_rate=Decimal('0'),
        )
        with self.assertRaises(ValidationError):
            profile.clean()

    def test_exempt_regime_rejects_positive_vat_rate(self):
        profile = EntityTaxProfile(
            tax_regime=EntityTaxProfile.TaxRegime.EXEMPT,
            default_vat_rate=Decimal('0.19'),
        )
        with self.assertRaises(ValidationError):
            profile.clean()
