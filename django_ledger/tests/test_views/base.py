"""
Shared fixtures and security helpers for view integration tests.

All entity-scoped view tests inherit ``DjangoLedgerViewTestCase``, which
extends ``DjangoLedgerBaseTest`` with:

  * a second unauthorized user + entity (cross-tenant leak checks)
  * lighter sample data so the suite stays practical
  * helpers for login-required, 403 cross-entity, GET-vs-POST actions, and
    happy-path 200/302 assertions
"""

from __future__ import annotations

from random import choice
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.urls import reverse

from django_ledger.models.entity import EntityModel
from django_ledger.tests.test_base import DjangoLedgerBaseTest

UserModel = get_user_model()


class DjangoLedgerViewTestCase(DjangoLedgerBaseTest):
    """
    Base for view tests.

    ``N`` / ``TX_QUANTITY`` / ``DAYS_FORWARD`` are intentionally smaller than
    the default generator settings so each TestCase class stays fast while
    still providing bills, invoices, JEs, customers, vendors, etc.
    """

    N = 1
    TX_QUANTITY = 5
    DAYS_FORWARD = 90

    OTHER_USERNAME = 'other-view-user'
    OTHER_PASSWORD = 'NeverUseThisPassword99999'
    OTHER_EMAIL = 'other-view-user@djangoledger.com'

    other_user = None
    other_entity: Optional[EntityModel] = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.other_user = UserModel.objects.create_user(
            username=cls.OTHER_USERNAME,
            password=cls.OTHER_PASSWORD,
            email=cls.OTHER_EMAIL,
        )
        cls.other_entity = EntityModel.create_entity(
            name='Unauthorized Other Entity',
            use_accrual_method=False,
            fy_start_month=1,
            admin=cls.other_user,
        )

    def setUp(self):
        # Fresh client login for every test method (self.client, not cls.CLIENT).
        self.client.logout()
        self.assertTrue(
            self.client.login(username=self.USERNAME, password=self.PASSWORD),
            msg='Failed to authenticate primary test user',
        )

    # ------------------------------------------------------------------
    # Entity / URL helpers
    # ------------------------------------------------------------------

    def get_entity(self) -> EntityModel:
        """
        Return an entity the *primary* test user may access.

        ``ENTITY_MODEL_QUERYSET`` includes the cross-tenant ``other_entity``;
        ``choice`` on that queryset breaks authorization and CoA setup in tests.
        """
        qs = EntityModel.objects.for_user(user_model=self.user_model)
        return choice(qs)

    def entity_kwargs(self, **extra) -> Dict[str, Any]:
        kwargs = {'entity_slug': self.get_entity().slug}
        kwargs.update(extra)
        return kwargs

    def reverse_entity(self, name: str, **extra) -> str:
        return reverse(f'django_ledger:{name}', kwargs=self.entity_kwargs(**extra))

    def foreign_entity_kwargs(self, **extra) -> Dict[str, Any]:
        """URL kwargs that point at an entity the primary user cannot access."""
        kwargs = {'entity_slug': self.other_entity.slug}
        kwargs.update(extra)
        return kwargs

    def reverse_foreign(self, name: str, **extra) -> str:
        return reverse(f'django_ledger:{name}', kwargs=self.foreign_entity_kwargs(**extra))

    # ------------------------------------------------------------------
    # Security / behavior assertions
    # ------------------------------------------------------------------

    def assert_login_required(self, url: str, method: str = 'get', **request_kwargs):
        """
        Anonymous users must be redirected to the login page.

        Re-authenticates the primary test user afterward so subsequent
        assertions in the same test method still run as an authorized user.
        """
        self.client.logout()
        http = getattr(self.client, method.lower())
        response = http(url, follow=False, **request_kwargs)
        self.assertEqual(
            response.status_code,
            302,
            msg=f'Expected login redirect for anonymous {method.upper()} {url}',
        )
        self.assertIn(
            reverse('django_ledger:login'),
            response.url,
            msg=f'Anonymous {method.upper()} {url} did not redirect to login',
        )
        self.assertTrue(
            self.client.login(username=self.USERNAME, password=self.PASSWORD),
            msg='Failed to re-authenticate primary test user after login_required check',
        )

    def assert_unauthorized_entity(self, url: str, method: str = 'get', **request_kwargs):
        """
        Authenticated but unauthorized entity access must not succeed.

        ``DjangoLedgerSecurityMixIn`` denies via PermissionRequiredMixin → 403.
        """
        http = getattr(self.client, method.lower())
        response = http(url, follow=False, **request_kwargs)
        self.assertEqual(
            response.status_code,
            403,
            msg=f'Expected 403 for unauthorized entity on {method.upper()} {url}, '
            f'got {response.status_code}',
        )

    def assert_get_ok(self, url: str, expected_status: int | tuple[int, ...] = 200):
        """
        Authenticated owner can GET the URL without server errors.

        ``expected_status`` may be a single code or an iterable (e.g. ``(200, 302)``
        for handler views that redirect to a dated report URL).
        """
        response = self.client.get(url, follow=False)
        if isinstance(expected_status, int):
            expected_status = (expected_status,)
        self.assertIn(
            response.status_code,
            expected_status,
            msg=f'GET {url} returned {response.status_code}, expected one of {expected_status}',
        )
        return response

    def assert_post_ok(
        self,
        url: str,
        data: Optional[dict] = None,
        expected_statuses=(302, 200),
    ):
        """
        Authenticated owner can POST without 4xx/5xx crashes.

        Actions typically redirect (302); form pages may re-render (200).
        """
        response = self.client.post(url, data=data or {}, follow=False)
        self.assertIn(
            response.status_code,
            expected_statuses,
            msg=f'POST {url} returned {response.status_code}, '
            f'expected one of {expected_statuses}',
        )
        return response

    def assert_action_requires_post(self, url: str):
        """
        Action endpoints reject GET when ``DJANGO_LEDGER_ACTION_VIEW_ALLOW_GET``
        is False (Django returns 405 Method Not Allowed).
        """
        response = self.client.get(url, follow=False)
        self.assertEqual(
            response.status_code,
            405,
            msg=f'Action GET {url} should be 405 when GET actions are disabled, '
            f'got {response.status_code}',
        )

    def assert_list_contains_no_foreign_entity(self, url: str, foreign_text: str):
        """List HTML for the authorized entity must not echo the other entity."""
        response = self.assert_get_ok(url)
        self.assertNotContains(response, foreign_text)

    def with_query(self, url: str, **params) -> str:
        if not params:
            return url
        sep = '&' if '?' in url else '?'
        return f'{url}{sep}{urlencode(params)}'
