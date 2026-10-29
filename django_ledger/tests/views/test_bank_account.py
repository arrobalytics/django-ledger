"""
View security and behavior tests for django_ledger.views.bank_account.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class BankAccountViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.bank_account'
