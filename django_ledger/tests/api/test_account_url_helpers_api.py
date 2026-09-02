"""
Smoke tests for AccountModel URL helpers.

These tests verify that account URL helpers resolve to entity/CoA/account
scoped strings without exercising view permissions or HTTP responses.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT
from django_ledger.models import AccountModel
from django_ledger.models.entity import EntityModel


class AccountURLHelpersAPITest(TestCase):
    ACCOUNT_SCOPED_URL_HELPERS = (
        "get_absolute_url",
        "get_update_url",
        "get_action_deactivate_url",
        "get_action_activate_url",
        "get_action_lock_url",
        "get_action_unlock_url",
    )

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_account_url_helpers_user",
            email="api-account-url-helpers-user@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.entity_model = EntityModel.create_entity(
            name="API Account URL Helpers Entity",
            admin=cls.user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        cls.coa_model = cls.entity_model.create_chart_of_accounts(
            coa_name="API Account URL Helpers CoA",
            commit=True,
            assign_as_default=True,
        )
        cls.entity_model.refresh_from_db()
        created_account = cls.coa_model.create_account(
            code="1010",
            name="API Account URL Helpers Cash",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
        )
        cls.account_model = AccountModel.objects.get(uuid=created_account.uuid)

    def assert_url_contains_entity_and_coa_slugs(self, url):
        self.assertIsInstance(url, str)
        self.assertTrue(url)
        self.assertIn(self.entity_model.slug, url)
        self.assertIn(self.coa_model.slug, url)

    def assert_url_contains_account_uuid(self, url):
        self.assertIn(str(self.account_model.uuid), url)

    def test_account_scoped_url_helpers_return_entity_coa_and_account_urls(self):
        urls_by_helper = {}

        for helper_name in self.ACCOUNT_SCOPED_URL_HELPERS:
            with self.subTest(helper_name=helper_name):
                url = getattr(self.account_model, helper_name)()
                urls_by_helper[helper_name] = url

                self.assert_url_contains_entity_and_coa_slugs(url)
                self.assert_url_contains_account_uuid(url)

        self.assertEqual(
            len(set(urls_by_helper.values())),
            len(self.ACCOUNT_SCOPED_URL_HELPERS),
        )

    def test_get_coa_account_list_url_returns_entity_and_coa_scoped_url(self):
        url = self.account_model.get_coa_account_list_url()

        self.assert_url_contains_entity_and_coa_slugs(url)
        self.assertNotIn(str(self.account_model.uuid), url)
