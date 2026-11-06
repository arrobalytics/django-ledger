"""View integration tests for entity URLs."""

from django.urls import reverse

from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class EntityViewTests(DjangoLedgerViewTestCase):
    """Entity list/create/dashboard/update — authorization and happy paths."""

    def test_entity_list_login_required(self):
        self.assert_login_required(reverse('django_ledger:entity-list'))

    def test_entity_list_get_ok(self):
        self.assert_get_ok(reverse('django_ledger:entity-list'))

    def test_entity_dashboard_login_required(self):
        self.assert_login_required(
            self.reverse_entity('entity-dashboard'),
        )

    def test_entity_dashboard_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(
            self.reverse_foreign('entity-dashboard'),
        )

    def test_entity_dashboard_get_ok(self):
        # EntityModelDetailHandlerView redirects to the current year dashboard.
        self.assert_get_ok(
            self.reverse_entity('entity-dashboard'),
            expected_status=302,
        )

    def test_entity_update_login_required(self):
        self.assert_login_required(self.reverse_entity('entity-update'))

    def test_entity_update_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('entity-update'))

    def test_entity_update_get_ok(self):
        self.assert_get_ok(self.reverse_entity('entity-update'))
