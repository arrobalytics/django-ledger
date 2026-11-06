"""
Financial statement URL integration tests (entity / ledger scoped).
"""

from __future__ import annotations

from django_ledger.io.io_core import get_localdate
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class FinancialStatementViewTests(DjangoLedgerViewTestCase):
    def _current_fiscal_year(self) -> int:
        return get_localdate().year

    def _assert_entity_statement_base_redirects_to_year(self, base_name: str, year_name: str):
        year = self._current_fiscal_year()
        base_url = self.reverse_entity(base_name)
        year_url = self.reverse_entity(year_name, year=year)

        response = self.client.get(base_url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, year_url)

        self.assert_get_ok(year_url)

    def test_entity_balance_sheet_and_year(self):
        self._assert_entity_statement_base_redirects_to_year('entity-bs', 'entity-bs-year')

    def test_entity_income_statement_and_year(self):
        self._assert_entity_statement_base_redirects_to_year('entity-ic', 'entity-ic-year')

    def test_entity_cash_flow_and_year(self):
        self._assert_entity_statement_base_redirects_to_year('entity-cf', 'entity-cf-year')

    def test_ledger_balance_sheet_redirects_with_ledger_pk(self):
        entity = self.get_entity()
        ledger = self.get_random_ledger(entity)
        year = self._current_fiscal_year()
        base_url = self.reverse_entity('ledger-bs', ledger_pk=ledger.uuid)
        year_url = self.reverse_entity('ledger-bs-year', ledger_pk=ledger.uuid, year=year)

        response = self.client.get(base_url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, year_url)

        self.assert_get_ok(year_url)

    def test_financial_statements_foreign_entity_403(self):
        year = self._current_fiscal_year()
        for name, extra in (
            ('entity-bs-year', {'year': year}),
            ('entity-ic-year', {'year': year}),
            ('entity-cf-year', {'year': year}),
        ):
            with self.subTest(url=name):
                url = self.reverse_foreign(name, **extra)
                self.assert_unauthorized_entity(url)
