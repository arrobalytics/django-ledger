"""View integration tests for bill URLs."""

from __future__ import annotations

from typing import Optional

from django.urls import reverse
from django.utils import timezone

from django_ledger.models import BillModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class BillModelViewTests(DjangoLedgerViewTestCase):
    def setUp(self):
        super().setUp()
        self.entity = self.get_entity()
        self.bills = self.entity.get_bills()

    def _pick(self, status: str) -> Optional[BillModel]:
        b = self.bills.filter(bill_status=status).first()
        return b

    def _urls(self, bill: BillModel):
        pk = bill.uuid
        dr = bill.date_draft or timezone.localdate()
        y, m = dr.year, dr.month
        return {
            'list': self.reverse_entity('bill-list'),
            'list_year': self.reverse_entity('bill-list-year', year=y),
            'list_month': self.reverse_entity('bill-list-month', year=y, month=m),
            'create': self.reverse_entity('bill-create'),
            'detail': self.reverse_entity('bill-detail', bill_pk=pk),
            'update': self.reverse_entity('bill-update', bill_pk=pk),
            'update_items': self.reverse_entity('bill-update-items', bill_pk=pk),
            'draft': self.reverse_entity('bill-action-mark-as-draft', bill_pk=pk),
            'review': self.reverse_entity('bill-action-mark-as-review', bill_pk=pk),
            'approved': self.reverse_entity('bill-action-mark-as-approved', bill_pk=pk),
            'paid': self.reverse_entity('bill-action-mark-as-paid', bill_pk=pk),
            'void': self.reverse_entity('bill-action-mark-as-void', bill_pk=pk),
            'canceled': self.reverse_entity('bill-action-mark-as-canceled', bill_pk=pk),
            'lock': self.reverse_entity('bill-action-lock-ledger', bill_pk=pk),
            'unlock': self.reverse_entity('bill-action-unlock-ledger', bill_pk=pk),
            'migrate': self.reverse_entity('bill-action-force-migrate', bill_pk=pk),
        }

    def test_list_requires_login(self):
        self.assert_login_required(self.reverse_entity('bill-list'))

    def test_create_requires_login(self):
        self.assert_login_required(self.reverse_entity('bill-create'))

    def test_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('bill-list'))

    def test_detail_foreign_entity_forbidden(self):
        bill = self.bills.first()
        if bill is None:
            self.skipTest('No bill in fixture data')
        url = reverse(
            'django_ledger:bill-detail',
            kwargs=self.foreign_entity_kwargs(bill_pk=bill.uuid),
        )
        self.assert_unauthorized_entity(url)

    def test_get_list_and_periods_ok(self):
        bill = self.bills.first()
        if bill is None:
            self.skipTest('No bill in fixture data')
        u = self._urls(bill)
        self.assert_get_ok(u['list'])
        self.assert_get_ok(u['list_year'])
        self.assert_get_ok(u['list_month'])

    def test_get_create_ok(self):
        self.assert_get_ok(self.reverse_entity('bill-create'))

    def test_get_detail_update_ok(self):
        bill = self.bills.first()
        if bill is None:
            self.skipTest('No bill in fixture data')
        u = self._urls(bill)
        self.assert_get_ok(u['detail'])
        self.assert_get_ok(u['update'])
        # Item-update route redirects to the bill update page on GET.
        self.assert_get_ok(u['update_items'], expected_status=302)

    def test_actions_get_method_not_allowed(self):
        bill = self.bills.first()
        if bill is None:
            self.skipTest('No bill in fixture data')
        u = self._urls(bill)
        for key in (
            'draft', 'review', 'approved', 'paid', 'void',
            'canceled', 'lock', 'unlock', 'migrate',
        ):
            self.assert_action_requires_post(u[key])

    def test_actions_post_ok(self):
        draft = self._pick(BillModel.BILL_STATUS_DRAFT)
        review = self._pick(BillModel.BILL_STATUS_REVIEW)
        approved = self._pick(BillModel.BILL_STATUS_APPROVED)
        paid = self._pick(BillModel.BILL_STATUS_PAID)

        if draft:
            self.assert_post_ok(self._urls(draft)['review'])
        if review:
            self.assert_post_ok(self._urls(review)['approved'])
        if approved:
            u = self._urls(approved)
            self.assert_post_ok(u['paid'])
            self.assert_post_ok(u['void'])
            self.assert_post_ok(u['lock'])
            self.assert_post_ok(u['unlock'])
            self.assert_post_ok(u['migrate'])
        if paid:
            self.assert_post_ok(self._urls(paid)['void'])

        cancel_candidate = self._pick(BillModel.BILL_STATUS_DRAFT)
        if cancel_candidate:
            self.assert_post_ok(self._urls(cancel_candidate)['canceled'])

        back_to_draft = self._pick(BillModel.BILL_STATUS_REVIEW)
        if back_to_draft:
            self.assert_post_ok(self._urls(back_to_draft)['draft'])
