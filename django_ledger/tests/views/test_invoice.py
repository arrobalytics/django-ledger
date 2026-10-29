"""
View security and behavior tests for django_ledger.views.invoice.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class InvoiceViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.invoice'
