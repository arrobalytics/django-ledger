"""
View security and behavior tests for django_ledger.views.djl_api.
"""
from django.urls import reverse

from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class DjlApiViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.djl_api'

    def test_api_endpoints_return_json_for_authorized_user(self):
        self.login_client()
        entity = self.get_entity_model()
        for name in ('entity-json-pnl', 'entity-json-net-payables', 'entity-json-net-receivables'):
            url = reverse(f'django_ledger:{name}', kwargs={'entity_slug': entity.slug})
            response = self.CLIENT.get(url)
            self.assertEqual(response.status_code, 200, msg=name)
            self.assertEqual(response['Content-Type'].split(';')[0], 'application/json')
