"""
View security and behavior tests for django_ledger.views.receipt.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class ReceiptViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.receipt'
    READ_OK_URL_NAMES = ('receipt-list', 'receipt-list-year', 'receipt-list-month')
