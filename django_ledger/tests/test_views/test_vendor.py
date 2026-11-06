"""View integration tests for vendor URLs."""

from __future__ import annotations

from random import choice

from django.urls import reverse

from django_ledger.models import VendorModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class VendorModelViewTests(DjangoLedgerViewTestCase):
    def setUp(self):
        super().setUp()
        self.entity = self.get_entity()
        qs = VendorModel.objects.for_entity(self.entity)
        self.vendor = choice(qs) if qs.exists() else None

    def _urls(self):
        assert self.vendor is not None
        pk = self.vendor.uuid
        return {
            'list': self.reverse_entity('vendor-list'),
            'create': self.reverse_entity('vendor-create'),
            'update': self.reverse_entity('vendor-update', vendor_pk=pk),
            'detail': self.reverse_entity('vendor-detail', vendor_pk=pk),
        }

    def test_list_requires_login(self):
        self.assert_login_required(self.reverse_entity('vendor-list'))

    def test_create_requires_login(self):
        self.assert_login_required(self.reverse_entity('vendor-create'))

    def test_detail_requires_login(self):
        if self.vendor is None:
            self.skipTest('No vendor in fixture data')
        self.assert_login_required(self._urls()['detail'])

    def test_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('vendor-list'))

    def test_detail_foreign_entity_forbidden(self):
        if self.vendor is None:
            self.skipTest('No vendor in fixture data')
        url = reverse(
            'django_ledger:vendor-detail',
            kwargs=self.foreign_entity_kwargs(vendor_pk=self.vendor.uuid),
        )
        self.assert_unauthorized_entity(url)

    def test_get_list_ok(self):
        self.assert_get_ok(self.reverse_entity('vendor-list'))

    def test_get_create_ok(self):
        self.assert_get_ok(self.reverse_entity('vendor-create'))

    def test_get_detail_ok(self):
        if self.vendor is None:
            self.skipTest('No vendor in fixture data')
        self.assert_get_ok(self._urls()['detail'])

    def test_get_update_ok(self):
        if self.vendor is None:
            self.skipTest('No vendor in fixture data')
        self.assert_get_ok(self._urls()['update'])
