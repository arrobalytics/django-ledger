"""
View security and behavior tests for django_ledger.views.ledger.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class LedgerViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.ledger'
