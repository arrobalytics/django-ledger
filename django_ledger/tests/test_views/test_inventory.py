"""View integration tests for inventory status and recount URLs."""

from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class InventoryViewTests(DjangoLedgerViewTestCase):
    """Inventory list (read-only) and recount (GET, optional confirm redirect)."""

    def test_inventory_list_login_required(self):
        self.assert_login_required(self.reverse_entity('inventory-list'))

    def test_inventory_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('inventory-list'))

    def test_inventory_list_get_ok(self):
        self.assert_get_ok(self.reverse_entity('inventory-list'))

    def test_inventory_recount_login_required(self):
        self.assert_login_required(self.reverse_entity('inventory-recount'))

    def test_inventory_recount_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('inventory-recount'))

    def test_inventory_recount_get_ok(self):
        self.assert_get_ok(self.reverse_entity('inventory-recount'))

    def test_inventory_recount_post_method_not_allowed(self):
        """Recount flow uses GET + optional ``confirm`` query param, not POST."""
        url = self.reverse_entity('inventory-recount')
        response = self.client.post(url, data={}, follow=False)
        self.assertEqual(
            response.status_code,
            405,
            msg=f'POST {url} should be 405, got {response.status_code}',
        )
