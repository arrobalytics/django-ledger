"""
View security and behavior tests for django_ledger.views.data_import.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class DataImportViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.data_import'
