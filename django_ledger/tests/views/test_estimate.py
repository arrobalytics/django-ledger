"""
View security and behavior tests for django_ledger.views.estimate.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class EstimateViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.estimate'
