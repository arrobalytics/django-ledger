"""
Integration tests for RootUrlView and DashboardView (``root`` and ``home`` URLs).
"""

from __future__ import annotations

from django.urls import reverse

from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class HomeDashboardViewTests(DjangoLedgerViewTestCase):
    def test_anonymous_root_redirects_to_login(self):
        self.client.logout()
        url = reverse('django_ledger:root')
        response = self.client.get(url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('django_ledger:login'))

    def test_authenticated_root_redirects_to_home_dashboard(self):
        url = reverse('django_ledger:root')
        home_url = reverse('django_ledger:home')
        response = self.client.get(url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, home_url)

    def test_home_requires_login(self):
        home_url = reverse('django_ledger:home')
        self.assert_login_required(home_url)

    def test_home_200_lists_entity(self):
        entity = self.get_entity()
        home_url = reverse('django_ledger:home')
        response = self.assert_get_ok(home_url)
        self.assertContains(response, entity.name)
