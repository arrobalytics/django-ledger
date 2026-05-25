from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from django_ledger_extensions.models import EntityTaxProfile
from django_ledger_countries.de.vat.reporting import (
    format_vat_quarterly_report,
    quarter_date_range,
    VatQuarterlyReport,
)
from django_ledger_countries.settings import clear_settings_cache


class QuarterDateRangeTests(SimpleTestCase):

    def test_q1_range(self):
        start, end = quarter_date_range(2026, 1)
        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 3, 31))


class VatReportFormattingTests(SimpleTestCase):

    def test_standard_report_shows_zahllast(self):
        report = VatQuarterlyReport(
            entity_slug='school',
            tax_regime=EntityTaxProfile.TaxRegime.STANDARD,
            year=2026,
            quarter=1,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            input_vat=Decimal('190.00'),
            output_vat=Decimal('380.00'),
            net_vat_payable=Decimal('190.00'),
            quarter_turnover=Decimal('2000.00'),
            ytd_turnover=Decimal('2000.00'),
            filing_summary='Pay ELSTER.',
        )
        text = format_vat_quarterly_report(report)
        self.assertIn('Vorsteuer', text)
        self.assertIn('190.00', text)
        self.assertIn('Zahllast', text)

    @override_settings(DJANGO_LEDGER_COUNTRY='de')
    def test_kleinunternehmer_report_mentions_no_voranmeldung(self):
        clear_settings_cache()
        report = VatQuarterlyReport(
            entity_slug='school',
            tax_regime=EntityTaxProfile.TaxRegime.SMALL_BUSINESS,
            year=2026,
            quarter=2,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 6, 30),
            quarter_turnover=Decimal('5000.00'),
            ytd_turnover=Decimal('12000.00'),
            prior_year_turnover=Decimal('18000.00'),
            filing_summary='Kleinunternehmer: no USt-Voranmeldung.',
        )
        text = format_vat_quarterly_report(report)
        self.assertIn('Kleinunternehmer', report.filing_summary)
        self.assertIn('5000.00', text)
