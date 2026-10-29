"""
View security and behavior tests for django_ledger.views.home.
"""
from django.urls import reverse

from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class HomeViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.home'

    def test_home_requires_login_and_renders_for_user(self):
        self.logout_client()
        home = reverse('django_ledger:home')
        self.assert_login_redirect(home)
        self.login_client()
        response = self.CLIENT.get(home, follow=False)
        # Dashboard may render or redirect into an entity workspace.
        self.assertIn(response.status_code, {200, 302})

    def test_root_redirect(self):
        response = self.CLIENT.get(reverse('django_ledger:root'), follow=False)
        self.assertIn(response.status_code, {301, 302})
