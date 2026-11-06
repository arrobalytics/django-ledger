"""
Feedback form views (POST-only): bug report and feature request.
"""

from __future__ import annotations

from django.urls import reverse

from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class FeedbackViewTests(DjangoLedgerViewTestCase):
    def test_bug_report_get_returns_405(self):
        url = reverse('django_ledger:bug-report')
        response = self.client.get(url, follow=False)
        self.assertEqual(response.status_code, 405)

    def test_new_feature_get_returns_405(self):
        url = reverse('django_ledger:new-feature')
        response = self.client.get(url, follow=False)
        self.assertEqual(response.status_code, 405)

    def test_bug_report_anonymous_post_redirects_to_login(self):
        self.client.logout()
        url = reverse('django_ledger:bug-report')
        response = self.client.post(
            url,
            data={
                'reproduce': 'steps',
                'expectation': 'expected',
                'device': 'desktop',
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('django_ledger:login'), response.url)

    def test_new_feature_anonymous_post_redirects_to_login(self):
        self.client.logout()
        url = reverse('django_ledger:new-feature')
        response = self.client.post(
            url,
            data={
                'feature_description': 'desc',
                'solution': 'solution',
                'alternatives': '',
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('django_ledger:login'), response.url)

    def test_bug_report_authenticated_post_no_server_error(self):
        url = reverse('django_ledger:bug-report')
        response = self.client.post(
            url,
            data={
                'reproduce': 'Repro steps',
                'expectation': 'Expected behavior',
                'device': 'desktop',
            },
            follow=False,
        )
        self.assertIn(response.status_code, (200, 302))
        self.assertLess(response.status_code, 500)

    def test_new_feature_authenticated_post_no_server_error(self):
        url = reverse('django_ledger:new-feature')
        response = self.client.post(
            url,
            data={
                'feature_description': 'Feature idea',
                'solution': 'Proposed solution',
                'alternatives': 'None',
            },
            follow=False,
        )
        self.assertIn(response.status_code, (200, 302))
        self.assertLess(response.status_code, 500)
