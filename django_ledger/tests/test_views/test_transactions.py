"""
``django_ledger.urls.transactions`` includes no URL patterns — the module is a stub.

Transaction editing in the UI is handled on journal entry detail (e.g. JE transaction
rows), not here. This import smoke-test documents that contract so a future mistaken
empty ``urlpatterns`` assignment stays visible in CI.
"""

from __future__ import annotations

from django.test import SimpleTestCase


class TransactionsUrlModuleTests(SimpleTestCase):
    def test_transactions_url_module_is_empty_placeholder(self):
        import django_ledger.urls.transactions as transactions_urls

        self.assertEqual(
            transactions_urls.urlpatterns,
            [],
            msg='transactions URL module should remain empty until dedicated views exist; '
            'use journal-entry detail for TX editing.',
        )
