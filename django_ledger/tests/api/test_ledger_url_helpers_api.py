"""
Smoke tests for LedgerModel URL and message helpers.

These tests verify that model helpers resolve to entity-scoped, ledger-scoped
strings without exercising view permissions or HTTP responses.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import LedgerModel
from django_ledger.models.entity import EntityModel


class LedgerURLHelpersAPITest(TestCase):
    ENTITY_SCOPED_URL_HELPERS = (
        "get_create_url",
        "get_list_url",
    )
    LEDGER_SCOPED_URL_HELPERS = (
        "get_absolute_url",
        "get_update_url",
        "get_journal_entry_list_url",
        "get_journal_entry_create_url",
        "get_balance_sheet_url",
        "get_income_statement_url",
        "get_cash_flow_statement_url",
        "get_action_post_journal_entries_url",
        "get_action_lock_journal_entries_url",
    )

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_ledger_url_helpers_admin",
            email="api-ledger-url-helpers-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.entity_model = EntityModel.create_entity(
            name="API Ledger URL Helpers Entity",
            admin=cls.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        cls.ledger_model = LedgerModel.objects.create(
            name="API Ledger URL Helpers Ledger",
            ledger_xid="api-ledger-url-helpers-ledger",
            entity=cls.entity_model,
        )

    def assert_url_contains_entity_slug(self, url):
        self.assertIsInstance(url, str)
        self.assertTrue(url)
        self.assertIn(self.entity_model.slug, url)

    def assert_url_contains_ledger_uuid(self, url):
        self.assertIn(str(self.ledger_model.uuid), url)

    def test_entity_scoped_url_helpers_return_entity_urls(self):
        for helper_name in self.ENTITY_SCOPED_URL_HELPERS:
            with self.subTest(helper_name=helper_name):
                url = getattr(self.ledger_model, helper_name)()

                self.assert_url_contains_entity_slug(url)

    def test_ledger_scoped_url_helpers_return_entity_and_ledger_urls(self):
        for helper_name in self.LEDGER_SCOPED_URL_HELPERS:
            with self.subTest(helper_name=helper_name):
                url = getattr(self.ledger_model, helper_name)()

                self.assert_url_contains_entity_slug(url)
                self.assert_url_contains_ledger_uuid(url)

    def test_get_delete_message_includes_ledger_and_entity_names(self):
        message = str(self.ledger_model.get_delete_message())

        self.assertIn(self.ledger_model.name, message)
        self.assertIn(self.entity_model.name, message)
