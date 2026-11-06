"""View integration tests for catalog item URLs (product, service, uom, expense, inventory items)."""

from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class ItemCatalogViewTests(DjangoLedgerViewTestCase):
    """Lists under ``django_ledger.urls.item``."""

    _LIST_NAMES = (
        'product-list',
        'service-list',
        'uom-list',
        'expense-list',
        'inventory-item-list',
    )

    def test_item_lists_login_required(self):
        for name in self._LIST_NAMES:
            with self.subTest(url_name=name):
                self.assert_login_required(self.reverse_entity(name))

    def test_item_lists_foreign_entity_forbidden(self):
        for name in self._LIST_NAMES:
            with self.subTest(url_name=name):
                self.assert_unauthorized_entity(self.reverse_foreign(name))

    def test_item_lists_get_ok(self):
        for name in self._LIST_NAMES:
            with self.subTest(url_name=name):
                self.assert_get_ok(self.reverse_entity(name))
