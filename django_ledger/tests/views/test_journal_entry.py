"""
View security and behavior tests for django_ledger.views.journal_entry.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class JournalEntryViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.journal_entry'
