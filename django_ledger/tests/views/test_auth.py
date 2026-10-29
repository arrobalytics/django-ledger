"""
View security and behavior tests for django_ledger.views.auth.
"""
from django.urls import reverse

from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class AuthViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.auth'
    PUBLIC_URL_NAMES = ('login', 'logout')

    def test_login_page_is_public(self):
        self.logout_client()
        response = self.CLIENT.get(reverse('django_ledger:login'))
        self.assertEqual(response.status_code, 200)

    def test_logout_post_logs_user_out(self):
        self.login_client()
        home = reverse('django_ledger:home')
        self.assertEqual(self.CLIENT.get(home).status_code, 200)
        response = self.CLIENT.post(reverse('django_ledger:logout'), follow=False)
        self.assertIn(response.status_code, {302, 200})
        self.assert_login_redirect(home)
