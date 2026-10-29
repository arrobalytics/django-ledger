"""
View security and behavior tests for django_ledger.views.customer.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class CustomerViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.customer'
