"""View integration tests for invoice URLs."""

from __future__ import annotations

from typing import Optional

from django.urls import reverse
from django.utils import timezone

from django_ledger.models import InvoiceModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class InvoiceModelViewTests(DjangoLedgerViewTestCase):
    def setUp(self):
        super().setUp()
        self.entity = self.get_entity()
        self.invoices = self.entity.get_invoices()

    def _pick(self, status: str) -> Optional[InvoiceModel]:
        return self.invoices.filter(invoice_status=status).first()

    def _urls(self, inv: InvoiceModel):
        pk = inv.uuid
        dr = inv.date_draft or timezone.localdate()
        y, m = dr.year, dr.month
        return {
            'list': self.reverse_entity('invoice-list'),
            'list_year': self.reverse_entity('invoice-list-year', year=y),
            'list_month': self.reverse_entity('invoice-list-month', year=y, month=m),
            'create': self.reverse_entity('invoice-create'),
            'detail': self.reverse_entity('invoice-detail', invoice_pk=pk),
            'update': self.reverse_entity('invoice-update', invoice_pk=pk),
            'update_items': self.reverse_entity('invoice-update-items', invoice_pk=pk),
            'delete': self.reverse_entity('invoice-delete', invoice_pk=pk),
            'draft': self.reverse_entity('invoice-action-mark-as-draft', invoice_pk=pk),
            'review': self.reverse_entity('invoice-action-mark-as-review', invoice_pk=pk),
            'approved': self.reverse_entity('invoice-action-mark-as-approved', invoice_pk=pk),
            'paid': self.reverse_entity('invoice-action-mark-as-paid', invoice_pk=pk),
            'void': self.reverse_entity('invoice-action-mark-as-void', invoice_pk=pk),
            'canceled': self.reverse_entity('invoice-action-mark-as-canceled', invoice_pk=pk),
            'migrate': self.reverse_entity('invoice-action-force-migrate', invoice_pk=pk),
            'lock': self.reverse_entity('invoice-action-lock-ledger', invoice_pk=pk),
            'unlock': self.reverse_entity('invoice-action-unlock-ledger', invoice_pk=pk),
        }

    def test_list_requires_login(self):
        self.assert_login_required(self.reverse_entity('invoice-list'))

    def test_create_requires_login(self):
        self.assert_login_required(self.reverse_entity('invoice-create'))

    def test_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('invoice-list'))

    def test_detail_foreign_entity_forbidden(self):
        inv = self.invoices.first()
        if inv is None:
            self.skipTest('No invoice in fixture data')
        url = reverse(
            'django_ledger:invoice-detail',
            kwargs=self.foreign_entity_kwargs(invoice_pk=inv.uuid),
        )
        self.assert_unauthorized_entity(url)

    def test_get_list_and_periods_ok(self):
        inv = self.invoices.first()
        if inv is None:
            self.skipTest('No invoice in fixture data')
        u = self._urls(inv)
        self.assert_get_ok(u['list'])
        self.assert_get_ok(u['list_year'])
        self.assert_get_ok(u['list_month'])

    def test_get_create_ok(self):
        self.assert_get_ok(self.reverse_entity('invoice-create'))

    def test_get_detail_update_delete_ok(self):
        inv = self.invoices.first()
        if inv is None:
            self.skipTest('No invoice in fixture data')
        u = self._urls(inv)
        self.assert_get_ok(u['detail'])
        self.assert_get_ok(u['update'])
        # Item-update route redirects to the invoice update page on GET.
        self.assert_get_ok(u['update_items'], expected_status=302)
        self.assert_get_ok(u['delete'])

    def test_actions_get_method_not_allowed(self):
        inv = self.invoices.first()
        if inv is None:
            self.skipTest('No invoice in fixture data')
        u = self._urls(inv)
        for key in (
            'draft', 'review', 'approved', 'paid', 'void',
            'canceled', 'migrate', 'lock', 'unlock',
        ):
            self.assert_action_requires_post(u[key])

    def test_actions_post_ok(self):
        draft = self._pick(InvoiceModel.INVOICE_STATUS_DRAFT)
        review = self._pick(InvoiceModel.INVOICE_STATUS_REVIEW)
        approved = self._pick(InvoiceModel.INVOICE_STATUS_APPROVED)
        paid = self._pick(InvoiceModel.INVOICE_STATUS_PAID)

        if draft:
            self.assert_post_ok(self._urls(draft)['review'])
        if review:
            self.assert_post_ok(self._urls(review)['approved'])
        if approved:
            u = self._urls(approved)
            self.assert_post_ok(u['paid'])
            self.assert_post_ok(u['void'])
            self.assert_post_ok(u['migrate'])
            self.assert_post_ok(u['lock'])
            self.assert_post_ok(u['unlock'])
        if paid:
            self.assert_post_ok(self._urls(paid)['void'])

        cancel_candidate = self._pick(InvoiceModel.INVOICE_STATUS_DRAFT)
        if cancel_candidate:
            self.assert_post_ok(self._urls(cancel_candidate)['canceled'])

        back_to_draft = self._pick(InvoiceModel.INVOICE_STATUS_REVIEW)
        if back_to_draft:
            self.assert_post_ok(self._urls(back_to_draft)['draft'])
