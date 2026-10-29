"""
View security and behavior tests for django_ledger.views.unit.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class UnitViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.unit'
