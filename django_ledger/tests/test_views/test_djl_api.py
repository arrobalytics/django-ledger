"""
JSON API view integration tests (PnL, net payables, net receivables).
"""

from __future__ import annotations

import json

from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class DjlApiViewTests(DjangoLedgerViewTestCase):
    _API_NAMES = (
        'entity-json-pnl',
        'entity-json-net-payables',
        'entity-json-net-receivables',
    )

    def test_api_login_required(self):
        for name in self._API_NAMES:
            with self.subTest(url=name):
                url = self.reverse_entity(name)
                self.assert_login_required(url)

    def test_api_unauthorized_entity_returns_403(self):
        for name in self._API_NAMES:
            with self.subTest(url=name):
                url = self.reverse_foreign(name)
                self.assert_unauthorized_entity(url)

    def test_api_authenticated_returns_json_200(self):
        for name in self._API_NAMES:
            with self.subTest(url=name):
                url = self.reverse_entity(name)
                response = self.assert_get_ok(url)
                self.assertEqual(response['Content-Type'][:16], 'application/json')
                payload = json.loads(response.content)
                self.assertIn('results', payload)
