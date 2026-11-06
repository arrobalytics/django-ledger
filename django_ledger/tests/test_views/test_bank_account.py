"""View integration tests for bank account URLs."""

from __future__ import annotations

from random import choice

from django.urls import reverse

from django_ledger.models import BankAccountModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class BankAccountModelViewTests(DjangoLedgerViewTestCase):
    def setUp(self):
        super().setUp()
        self.entity = self.get_entity()
        qs = BankAccountModel.objects.for_entity(self.entity)
        self.bank_account = choice(qs) if qs.exists() else None

    def _urls(self):
        assert self.bank_account is not None
        pk = self.bank_account.uuid
        return {
            'list': self.reverse_entity('bank-account-list'),
            'create': self.reverse_entity('bank-account-create'),
            'update': self.reverse_entity('bank-account-update', bank_account_pk=pk),
            'active': self.reverse_entity('bank-account-mark-as-active', bank_account_pk=pk),
            'inactive': self.reverse_entity(
                'bank-account-mark-as-inactive', bank_account_pk=pk
            ),
        }

    def test_list_requires_login(self):
        self.assert_login_required(self.reverse_entity('bank-account-list'))

    def test_create_requires_login(self):
        self.assert_login_required(self.reverse_entity('bank-account-create'))

    def test_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('bank-account-list'))

    def test_update_foreign_entity_forbidden(self):
        if self.bank_account is None:
            self.skipTest('No bank account in fixture data')
        url = reverse(
            'django_ledger:bank-account-update',
            kwargs=self.foreign_entity_kwargs(bank_account_pk=self.bank_account.uuid),
        )
        self.assert_unauthorized_entity(url)

    def test_get_list_ok(self):
        self.assert_get_ok(self.reverse_entity('bank-account-list'))

    def test_get_create_ok(self):
        self.assert_get_ok(self.reverse_entity('bank-account-create'))

    def test_get_update_ok(self):
        if self.bank_account is None:
            self.skipTest('No bank account in fixture data')
        self.assert_get_ok(self._urls()['update'])

    def test_actions_get_method_not_allowed(self):
        if self.bank_account is None:
            self.skipTest('No bank account in fixture data')
        u = self._urls()
        self.assert_action_requires_post(u['active'])
        self.assert_action_requires_post(u['inactive'])

    def test_actions_post_ok(self):
        if self.bank_account is None:
            self.skipTest('No bank account in fixture data')
        u = self._urls()
        self.assert_post_ok(u['active'])
        self.assert_post_ok(u['inactive'])
