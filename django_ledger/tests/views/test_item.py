"""
View security and behavior tests for django_ledger.views.item.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class ItemViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.item'
