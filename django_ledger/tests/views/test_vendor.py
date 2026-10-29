"""
View security and behavior tests for django_ledger.views.vendor.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class VendorViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.vendor'
