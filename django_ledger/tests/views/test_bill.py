"""
View security and behavior tests for django_ledger.views.bill.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class BillViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.bill'
