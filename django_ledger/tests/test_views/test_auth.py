"""
Login / logout view integration tests (complement ``AuthTest`` in test_base).
"""

from __future__ import annotations

from django.urls import reverse

from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class AuthPageViewTests(DjangoLedgerViewTestCase):
    def test_get_login_returns_200(self):
        login_url = reverse('django_ledger:login')
        self.assert_get_ok(login_url)

    def test_logout_get_when_logged_in_requires_post(self):
        logout_url = reverse('django_ledger:logout')
        response = self.client.get(logout_url, follow=False)
        self.assertEqual(response.status_code, 405)

    def test_get_protected_home_after_logout_redirects_to_login(self):
        home_url = reverse('django_ledger:home')
        logout_url = reverse('django_ledger:logout')
        self.client.post(logout_url, follow=False)
        response = self.client.get(home_url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('django_ledger:login'), response.url)
