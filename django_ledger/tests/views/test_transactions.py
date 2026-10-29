"""
View security and behavior tests for django_ledger.views.transactions.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class TransactionsViewTests(DjangoLedgerViewTestCase):

    def test_transactions_url_module_has_no_patterns(self):
        """transactions views module is a stub; URL module exposes no routes."""
        import django_ledger.urls.transactions as tx_urls
        self.assertEqual(list(tx_urls.urlpatterns), [])
