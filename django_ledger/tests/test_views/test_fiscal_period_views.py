"""
Integration tests for fiscal year windows on report views.

An EntityModel whose fiscal year starts in April must produce April-based windows on every report view that reaches
EntityModelFiscalPeriodMixIn: entity, ledger and unit statements, account detail and the receipt quarter list.
"""

from datetime import date

from django_ledger.models.entity import EntityModel
from django_ledger.models.unit import EntityUnitModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class FiscalPeriodReportViewTest(DjangoLedgerViewTestCase):
    """Report views read the fiscal year start month from the EntityModel behind the page."""

    FY_START_MONTH = 4
    REPORT_YEAR = 2024
    EXPECTED_YEAR_START = date(2024, 4, 1)
    EXPECTED_YEAR_END = date(2025, 3, 31)

    def setUp(self):
        super().setUp()
        self.entity_model = self.get_entity()
        EntityModel.objects.filter(uuid=self.entity_model.uuid).update(fy_start_month=self.FY_START_MONTH)

    def assert_year_window(self, url: str):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['year_start'], self.EXPECTED_YEAR_START)
        self.assertEqual(response.context['year_end'], self.EXPECTED_YEAR_END)

    def test_entity_balance_sheet_year_starts_in_april(self):
        self.assert_year_window(self.reverse_entity('entity-bs-year', year=self.REPORT_YEAR))

    def test_ledger_balance_sheet_year_starts_in_april(self):
        ledger_model = self.entity_model.ledgermodel_set.first()
        self.assert_year_window(self.reverse_entity('ledger-bs-year', ledger_pk=ledger_model.uuid, year=self.REPORT_YEAR))

    def test_unit_balance_sheet_year_starts_in_april(self):
        unit_model = EntityUnitModel.objects.filter(entity=self.entity_model).first()
        self.assertIsNotNone(unit_model)
        self.assert_year_window(self.reverse_entity('unit-bs-year', unit_slug=unit_model.slug, year=self.REPORT_YEAR))

    def test_account_detail_year_starts_in_april(self):
        coa_model = self.entity_model.get_default_coa()
        account_model = self.entity_model.get_coa_accounts(coa_model=coa_model).first()
        url = self.reverse_entity(
            'account-detail-year',
            coa_slug=coa_model.slug,
            account_pk=account_model.uuid,
            year=self.REPORT_YEAR,
        )
        self.assert_year_window(url)

    def test_receipt_quarter_list_uses_the_authorized_entity(self):
        response = self.client.get(self.reverse_entity('receipt-list-quarter', year=self.REPORT_YEAR, quarter=1))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['quarter_start'], self.EXPECTED_YEAR_START)
        self.assertEqual(response.context['quarter_end'], date(2024, 6, 30))
