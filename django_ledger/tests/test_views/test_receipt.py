"""
Receipt list/detail view integration tests.
"""

from __future__ import annotations

from django.urls import reverse

from django_ledger.models.receipt import ReceiptModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class ReceiptViewTests(DjangoLedgerViewTestCase):
    def test_receipt_list_login_required(self):
        url = self.reverse_entity('receipt-list')
        self.assert_login_required(url)

    def test_receipt_list_unauthorized_403(self):
        url = self.reverse_foreign('receipt-list')
        self.assert_unauthorized_entity(url)

    def test_receipt_list_authenticated_200(self):
        url = self.reverse_entity('receipt-list')
        self.assert_get_ok(url)

    def test_receipt_detail_200_when_receipt_exists_for_entity(self):
        entity = self.get_entity()
        receipt = ReceiptModel.objects.for_entity(entity).first()
        if receipt is None:
            self.skipTest('No ReceiptModel for test entity; creating one is out of scope.')
        url = reverse(
            'django_ledger:receipt-detail',
            kwargs={'entity_slug': entity.slug, 'receipt_pk': receipt.pk},
        )
        self.assert_get_ok(url)
