"""View integration tests for ledger URLs."""

from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class LedgerViewTests(DjangoLedgerViewTestCase):
    """Ledger list/detail and action views."""

    def test_ledger_list_login_required(self):
        self.assert_login_required(self.reverse_entity('ledger-list'))

    def test_ledger_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('ledger-list'))

    def test_ledger_list_current_get_ok(self):
        self.assert_get_ok(self.reverse_entity('ledger-list'))

    def test_ledger_detail_login_required(self):
        ledger = self.get_random_ledger(entity_model=self.get_entity())
        self.assert_login_required(
            self.reverse_entity('ledger-detail', ledger_pk=ledger.uuid),
        )

    def test_ledger_detail_foreign_entity_forbidden(self):
        # Use an authorized ledger PK under a foreign slug — security mixin 403s first.
        ledger = self.get_random_ledger(entity_model=self.get_entity())
        self.assert_unauthorized_entity(
            self.reverse_foreign('ledger-detail', ledger_pk=ledger.uuid),
        )

    def test_ledger_detail_get_ok(self):
        ledger = self.get_random_ledger(entity_model=self.get_entity())
        self.assert_get_ok(self.reverse_entity('ledger-detail', ledger_pk=ledger.uuid))

    def test_ledger_visible_and_all_get_ok(self):
        self.assert_get_ok(self.reverse_entity('ledger-list-visible'))
        self.assert_get_ok(self.reverse_entity('ledger-list-all'))

    def test_ledger_create_get_ok(self):
        self.assert_get_ok(self.reverse_entity('ledger-create'))

    def test_ledger_update_and_delete_get_ok(self):
        ledger = self.get_random_ledger(entity_model=self.get_entity())
        self.assert_get_ok(self.reverse_entity('ledger-update', ledger_pk=ledger.uuid))
        self.assert_get_ok(self.reverse_entity('ledger-delete', ledger_pk=ledger.uuid))

    def test_ledger_action_hide_login_and_foreign_forbidden(self):
        ledger = self.get_random_ledger(entity_model=self.get_entity())
        ok_url = self.reverse_entity('ledger-action-hide', ledger_pk=ledger.uuid)
        self.assert_login_required(ok_url, method='post')
        self.assert_unauthorized_entity(
            self.reverse_foreign('ledger-action-hide', ledger_pk=ledger.uuid),
            method='post',
        )

    def test_ledger_action_hide_post_ok(self):
        ledger = self.get_random_ledger(entity_model=self.get_entity())
        url = self.reverse_entity('ledger-action-hide', ledger_pk=ledger.uuid)
        self.assert_post_ok(url)

    def test_ledger_action_hide_get_method_not_allowed(self):
        ledger = self.get_random_ledger(entity_model=self.get_entity())
        self.assert_action_requires_post(
            self.reverse_entity('ledger-action-hide', ledger_pk=ledger.uuid),
        )
