"""
View security and behavior tests for django_ledger.views.account.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class AccountViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.account'
