"""View integration tests for customer URLs."""

from __future__ import annotations

from random import choice

from django.urls import reverse

from django_ledger.models import CustomerModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class CustomerModelViewTests(DjangoLedgerViewTestCase):
    def setUp(self):
        super().setUp()
        self.entity = self.get_entity()
        qs = CustomerModel.objects.for_entity(self.entity)
        self.customer = choice(qs) if qs.exists() else None

    def _urls(self):
        assert self.customer is not None
        pk = self.customer.uuid
        return {
            'list': self.reverse_entity('customer-list'),
            'create': self.reverse_entity('customer-create'),
            'update': self.reverse_entity('customer-update', customer_pk=pk),
            'detail': self.reverse_entity('customer-detail', customer_pk=pk),
        }

    def test_list_requires_login(self):
        self.assert_login_required(self.reverse_entity('customer-list'))

    def test_create_requires_login(self):
        self.assert_login_required(self.reverse_entity('customer-create'))

    def test_detail_requires_login(self):
        if self.customer is None:
            self.skipTest('No customer in fixture data')
        self.assert_login_required(self._urls()['detail'])

    def test_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('customer-list'))

    def test_detail_foreign_entity_forbidden(self):
        if self.customer is None:
            self.skipTest('No customer in fixture data')
        url = reverse(
            'django_ledger:customer-detail',
            kwargs=self.foreign_entity_kwargs(customer_pk=self.customer.uuid),
        )
        self.assert_unauthorized_entity(url)

    def test_get_list_ok(self):
        self.assert_get_ok(self.reverse_entity('customer-list'))

    def test_get_create_ok(self):
        self.assert_get_ok(self.reverse_entity('customer-create'))

    def test_get_detail_ok(self):
        if self.customer is None:
            self.skipTest('No customer in fixture data')
        self.assert_get_ok(self._urls()['detail'])

    def test_get_update_ok(self):
        if self.customer is None:
            self.skipTest('No customer in fixture data')
        self.assert_get_ok(self._urls()['update'])
