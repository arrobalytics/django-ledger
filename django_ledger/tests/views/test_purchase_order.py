"""
View security and behavior tests for django_ledger.views.purchase_order.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class PurchaseOrderViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.purchase_order'
