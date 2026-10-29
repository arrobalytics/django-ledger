"""
View security and behavior tests for django_ledger.views.closing_entry.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class ClosingEntryViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.closing_entry'
