"""
View security and behavior tests for django_ledger.views.feedback.
"""
from django.urls import reverse

from django_ledger.tests.views.base import DjangoLedgerViewTestCase


class FeedbackViewTests(DjangoLedgerViewTestCase):
    URL_MODULE = 'django_ledger.urls.feedback'
    # Feedback endpoints are POST-only form handlers.
    EXTRA_ACTION_URL_NAMES = ('bug-report', 'new-feature')
    READ_OK_URL_NAMES = ()

    def test_feedback_urls_reject_get(self):
        self.login_client()
        for name in ('bug-report', 'new-feature'):
            url = reverse(f'django_ledger:{name}')
            response = self.CLIENT.get(url, follow=False)
            self.assertEqual(response.status_code, 405, msg=name)
