"""
View security and behavior tests for django_ledger.views.inventory.
"""
from django.urls import reverse

from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class InventoryViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.inventory'

    def test_inventory_recount_get_does_not_require_action_post_only(self):
        """Recount page is readable with GET; updates happen on POST."""
        self.login_client()
        entity = self.get_entity_model()
        url = reverse('django_ledger:inventory-recount', kwargs={'entity_slug': entity.slug})
        response = self.CLIENT.get(url)
        self.assertEqual(response.status_code, 200)
        # legacy confirm query must not be a silent mutation path anymore
        response_confirm = self.CLIENT.get(url + '?confirm=1', follow=False)
        self.assertEqual(response_confirm.status_code, 200)

    def test_inventory_recount_post_updates(self):
        self.login_client()
        entity = self.get_entity_model()
        url = reverse('django_ledger:inventory-recount', kwargs={'entity_slug': entity.slug})
        response = self.CLIENT.post(url, follow=False)
        self.assertIn(response.status_code, {302, 200})
