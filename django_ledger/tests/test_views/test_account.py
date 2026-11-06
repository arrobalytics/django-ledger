"""View integration tests for entity-scoped account URLs."""

from __future__ import annotations

from random import choice

from django.urls import reverse

from django_ledger.models import AccountModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class AccountModelViewTests(DjangoLedgerViewTestCase):
    def setUp(self):
        super().setUp()
        self.entity = self.get_entity()
        self.coa = self.entity.get_default_coa()
        account_qs = self.entity.get_coa_accounts(coa_model=self.coa)
        self.account: AccountModel = choice(list(account_qs))

    def _acct_urls(self):
        base = {'coa_slug': self.coa.slug, 'account_pk': self.account.uuid}
        y, m, d = (
            self.account.created.year,
            self.account.created.month,
            self.account.created.day,
        )
        return {
            'list': self.reverse_entity('account-list', coa_slug=self.coa.slug),
            'list_active': self.reverse_entity('account-list-active', coa_slug=self.coa.slug),
            'create': self.reverse_entity('account-create', coa_slug=self.coa.slug),
            'update': self.reverse_entity('account-update', **base),
            'detail': self.reverse_entity('account-detail', **base),
            'detail_year': self.reverse_entity('account-detail-year', year=y, **base),
            'detail_quarter': self.reverse_entity(
                'account-detail-quarter', year=y, quarter=1, **base
            ),
            'detail_month': self.reverse_entity('account-detail-month', year=y, month=m, **base),
            'detail_date': self.reverse_entity(
                'account-detail-date', year=y, month=m, day=d, **base
            ),
            'activate': self.reverse_entity('account-action-activate', **base),
            'deactivate': self.reverse_entity('account-action-deactivate', **base),
            'lock': self.reverse_entity('account-action-lock', **base),
            'unlock': self.reverse_entity('account-action-unlock', **base),
        }

    def test_list_requires_login(self):
        self.assert_login_required(self._acct_urls()['list'])

    def test_list_active_requires_login(self):
        self.assert_login_required(self._acct_urls()['list_active'])

    def test_create_requires_login(self):
        self.assert_login_required(self._acct_urls()['create'])

    def test_update_requires_login(self):
        self.assert_login_required(self._acct_urls()['update'])

    def test_detail_requires_login(self):
        self.assert_login_required(self._acct_urls()['detail'])

    def test_list_foreign_entity_forbidden(self):
        url = reverse(
            'django_ledger:account-list',
            kwargs=self.foreign_entity_kwargs(coa_slug=self.coa.slug),
        )
        self.assert_unauthorized_entity(url)

    def test_detail_foreign_entity_forbidden(self):
        url = reverse(
            'django_ledger:account-detail',
            kwargs=self.foreign_entity_kwargs(
                coa_slug=self.coa.slug,
                account_pk=self.account.uuid,
            ),
        )
        self.assert_unauthorized_entity(url)

    def test_get_list_ok(self):
        self.assert_get_ok(self._acct_urls()['list'])

    def test_get_list_active_ok(self):
        self.assert_get_ok(self._acct_urls()['list_active'])

    def test_get_create_ok(self):
        self.assert_get_ok(self._acct_urls()['create'])

    def test_get_update_ok(self):
        self.assert_get_ok(self._acct_urls()['update'])

    def test_get_detail_ok(self):
        # AccountModelDetailView is a RedirectView → dated detail URL.
        self.assert_get_ok(self._acct_urls()['detail'], expected_status=302)

    def test_get_detail_period_urls_ok(self):
        u = self._acct_urls()
        for key in ('detail_year', 'detail_quarter', 'detail_month', 'detail_date'):
            self.assert_get_ok(u[key])

    def test_actions_get_method_not_allowed(self):
        u = self._acct_urls()
        for key in ('activate', 'deactivate', 'lock', 'unlock'):
            self.assert_action_requires_post(u[key])

    def test_actions_post_ok(self):
        u = self._acct_urls()
        self.assert_post_ok(u['unlock'])
        self.assert_post_ok(u['lock'])
        self.assert_post_ok(u['activate'])
        self.assert_post_ok(u['deactivate'])
