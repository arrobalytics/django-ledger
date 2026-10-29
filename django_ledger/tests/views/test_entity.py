"""
View security and behavior tests for django_ledger.views.entity.
"""
from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class EntityViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.entity'
    READ_OK_URL_NAMES = ('entity-list', 'entity-create', 'entity-dashboard', 'entity-update')
