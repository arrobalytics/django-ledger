"""View integration tests for closing entry URLs."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from django.urls import reverse

from django_ledger.io.io_core import get_localdate
from django_ledger.models import BillModel, ClosingEntryModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class ClosingEntryModelViewTests(DjangoLedgerViewTestCase):
    def setUp(self):
        super().setUp()
        self.entity = self.get_entity()
        self.closing_date = self._pick_closing_date()
        self.ce_model: ClosingEntryModel
        try:
            self.ce_model, _ = self.entity.close_entity_books(
                closing_date=self.closing_date,
                force_update=True,
                post_closing_entry=False,
            )
        except Exception as exc:
            existing = self.entity.closingentrymodel_set.order_by('-closing_date').first()
            if existing is None:
                self.skipTest(f'Could not create or load a closing entry: {exc}')
            self.ce_model = existing
            self.closing_date = existing.closing_date

    def _pick_closing_date(self) -> date:
        bill = BillModel.objects.for_entity(self.entity).order_by('date_draft').first()
        if bill and bill.date_draft:
            d = bill.date_draft
        else:
            d = get_localdate() - timedelta(days=30)
        last_day = monthrange(d.year, d.month)[1]
        return date(d.year, d.month, last_day)

    def _urls(self):
        pk = self.ce_model.uuid
        y, m = self.closing_date.year, self.closing_date.month
        return {
            'list': self.reverse_entity('closing-entry-list'),
            'list_year': self.reverse_entity('closing-entry-list-year', year=y),
            'list_month': self.reverse_entity('closing-entry-list-month', year=y, month=m),
            'create': self.reverse_entity('closing-entry-create'),
            'detail': self.reverse_entity('closing-entry-detail', closing_entry_pk=pk),
            'update': self.reverse_entity('closing-entry-update', closing_entry_pk=pk),
            'delete': self.reverse_entity('closing-entry-delete', closing_entry_pk=pk),
            'post': self.reverse_entity('closing-entry-action-mark-as-posted', closing_entry_pk=pk),
            'unpost': self.reverse_entity('closing-entry-action-mark-as-unposted', closing_entry_pk=pk),
            'update_txs': self.reverse_entity('closing-entry-action-update-txs', closing_entry_pk=pk),
        }

    def test_list_requires_login(self):
        self.assert_login_required(self._urls()['list'])

    def test_create_requires_login(self):
        self.assert_login_required(self._urls()['create'])

    def test_detail_requires_login(self):
        self.assert_login_required(self._urls()['detail'])

    def test_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('closing-entry-list'))

    def test_detail_foreign_entity_forbidden(self):
        url = reverse(
            'django_ledger:closing-entry-detail',
            kwargs=self.foreign_entity_kwargs(closing_entry_pk=self.ce_model.uuid),
        )
        self.assert_unauthorized_entity(url)

    def test_get_list_ok(self):
        self.assert_get_ok(self._urls()['list'])

    def test_get_year_month_list_ok(self):
        u = self._urls()
        self.assert_get_ok(u['list_year'])
        self.assert_get_ok(u['list_month'])

    def test_get_create_ok(self):
        self.assert_get_ok(self._urls()['create'])

    def test_get_detail_update_delete_ok(self):
        u = self._urls()
        self.assert_get_ok(u['detail'])
        self.assert_get_ok(u['update'])
        self.assert_get_ok(u['delete'])

    def test_actions_get_method_not_allowed(self):
        u = self._urls()
        for key in ('post', 'unpost', 'update_txs'):
            self.assert_action_requires_post(u[key])

    def test_actions_post_ok(self):
        u = self._urls()
        self.assert_post_ok(u['update_txs'])
        self.assert_post_ok(u['post'])
        self.assert_post_ok(u['unpost'])
