"""
View security and behavior tests for django_ledger.views.financial_statement.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class FinancialStatementViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.financial_statement'
    READ_OK_URL_NAMES = ('entity-bs', 'entity-ic', 'entity-cf', 'entity-bs-year', 'entity-ic-year', 'entity-cf-year')
