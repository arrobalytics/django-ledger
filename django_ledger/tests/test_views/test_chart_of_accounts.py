"""View integration tests for chart-of-accounts URLs."""

from __future__ import annotations

from random import choice

from django.urls import reverse

from django_ledger.models import ChartOfAccountModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class ChartOfAccountsViewTests(DjangoLedgerViewTestCase):
    def setUp(self):
        super().setUp()
        self.entity = self.get_entity()
        qs = ChartOfAccountModel.objects.filter(entity=self.entity)
        self.coa = choice(qs) if qs.exists() else self.entity.get_default_coa()
        self.non_default_coa = (
            qs.exclude(uuid=self.entity.default_coa_id).first()
            if qs.exclude(uuid=self.entity.default_coa_id).exists()
            else None
        )
        if self.non_default_coa is None:
            self.non_default_coa = self.entity.create_chart_of_accounts(
                assign_as_default=False,
                coa_name='Integration Test CoA',
                commit=True,
            )

    def _urls(self):
        slug = self.coa.slug
        return {
            'list': self.reverse_entity('coa-list'),
            'list_inactive': self.reverse_entity('coa-list-inactive'),
            'create': self.reverse_entity('coa-create'),
            'detail': self.reverse_entity('coa-detail', coa_slug=slug),
            'update': self.reverse_entity('coa-update', coa_slug=slug),
            'mark_default': self.reverse_entity('coa-action-mark-as-default', coa_slug=slug),
            'mark_active': self.reverse_entity('coa-action-mark-as-active', coa_slug=slug),
            'mark_inactive': self.reverse_entity('coa-action-mark-as-inactive', coa_slug=slug),
        }

    def test_list_requires_login(self):
        self.assert_login_required(self._urls()['list'])

    def test_list_inactive_requires_login(self):
        self.assert_login_required(self._urls()['list_inactive'])

    def test_create_requires_login(self):
        self.assert_login_required(self._urls()['create'])

    def test_detail_requires_login(self):
        self.assert_login_required(self._urls()['detail'])

    def test_update_requires_login(self):
        self.assert_login_required(self._urls()['update'])

    def test_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('coa-list'))

    def test_detail_foreign_entity_forbidden(self):
        url = reverse(
            'django_ledger:coa-detail',
            kwargs=self.foreign_entity_kwargs(coa_slug=self.coa.slug),
        )
        self.assert_unauthorized_entity(url)

    def test_get_list_ok(self):
        self.assert_get_ok(self._urls()['list'])

    def test_get_list_inactive_ok(self):
        self.assert_get_ok(self._urls()['list_inactive'])

    def test_get_create_ok(self):
        self.assert_get_ok(self._urls()['create'])

    def test_get_detail_ok(self):
        self.assert_get_ok(self._urls()['detail'])

    def test_get_update_ok(self):
        self.assert_get_ok(self._urls()['update'])

    def test_actions_get_method_not_allowed(self):
        u = self._urls()
        self.assert_action_requires_post(u['mark_default'])
        self.assert_action_requires_post(u['mark_active'])
        self.assert_action_requires_post(u['mark_inactive'])

    def test_actions_post_ok(self):
        slug = self.non_default_coa.slug
        mark_active = self.reverse_entity('coa-action-mark-as-active', coa_slug=slug)
        mark_inactive = self.reverse_entity('coa-action-mark-as-inactive', coa_slug=slug)
        mark_default = self.reverse_entity('coa-action-mark-as-default', coa_slug=slug)
        self.assert_post_ok(mark_active)
        self.assert_post_ok(mark_inactive)
        self.assert_post_ok(mark_active)
        self.assert_post_ok(mark_default)
