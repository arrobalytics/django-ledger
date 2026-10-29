"""
View security and behavior tests for django_ledger.views.chart_of_accounts.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class ChartOfAccountsViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.chart_of_accounts'
