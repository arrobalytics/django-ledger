"""
Smoke tests for JournalEntryModel URL and message helpers.

These tests verify that model helpers resolve to entity-scoped, ledger-scoped,
and journal-entry-scoped strings without exercising view permissions or HTTP
responses.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel
from django_ledger.models.entity import EntityModel


class JournalEntryURLHelpersAPITest(TestCase):
    LEDGER_SCOPED_URL_HELPERS = (
        "get_journal_entry_list_url",
        "get_journal_entry_create_url",
    )
    JOURNAL_ENTRY_SCOPED_URL_HELPERS = (
        "get_absolute_url",
        "get_detail_url",
        "get_detail_txs_url",
        "get_unlock_url",
        "get_lock_url",
        "get_post_url",
        "get_unpost_url",
        "get_action_post_url",
        "get_action_unpost_url",
        "get_action_lock_url",
        "get_action_unlock_url",
    )

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_je_url_helpers_admin",
            email="api-je-url-helpers-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.entity_model = EntityModel.create_entity(
            name="API Journal Entry URL Helpers Entity",
            admin=cls.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        cls.ledger_model = LedgerModel.objects.create(
            name="API Journal Entry URL Helpers Ledger",
            ledger_xid="api-je-url-helpers-ledger",
            entity=cls.entity_model,
        )
        cls.journal_entry = JournalEntryModel.objects.create(
            ledger=cls.ledger_model,
            timestamp=cls.make_timestamp(),
            description="API Journal Entry URL Helpers Journal Entry",
        )

    @classmethod
    def make_timestamp(cls):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def assert_url_contains_entity_slug(self, url):
        self.assertIsInstance(url, str)
        self.assertTrue(url)
        self.assertIn(self.entity_model.slug, url)

    def assert_url_contains_ledger_uuid(self, url):
        self.assertIn(str(self.ledger_model.uuid), url)

    def assert_url_contains_journal_entry_uuid(self, url):
        self.assertIn(str(self.journal_entry.uuid), url)

    def test_ledger_scoped_url_helpers_return_entity_and_ledger_urls(self):
        for helper_name in self.LEDGER_SCOPED_URL_HELPERS:
            with self.subTest(helper_name=helper_name):
                url = getattr(self.journal_entry, helper_name)()

                self.assert_url_contains_entity_slug(url)
                self.assert_url_contains_ledger_uuid(url)

    def test_journal_entry_scoped_url_helpers_return_entity_ledger_and_entry_urls(self):
        for helper_name in self.JOURNAL_ENTRY_SCOPED_URL_HELPERS:
            with self.subTest(helper_name=helper_name):
                url = getattr(self.journal_entry, helper_name)()

                self.assert_url_contains_entity_slug(url)
                self.assert_url_contains_ledger_uuid(url)
                self.assert_url_contains_journal_entry_uuid(url)

    def test_detail_url_matches_absolute_url(self):
        self.assertEqual(
            self.journal_entry.get_absolute_url(),
            self.journal_entry.get_detail_url(),
        )

    def test_action_url_aliases_match_matching_url_helpers(self):
        self.assertEqual(
            self.journal_entry.get_post_url(),
            self.journal_entry.get_action_post_url(),
        )
        self.assertEqual(
            self.journal_entry.get_unpost_url(),
            self.journal_entry.get_action_unpost_url(),
        )
        self.assertEqual(
            self.journal_entry.get_lock_url(),
            self.journal_entry.get_action_lock_url(),
        )
        self.assertEqual(
            self.journal_entry.get_unlock_url(),
            self.journal_entry.get_action_unlock_url(),
        )

    def test_get_delete_message_includes_journal_entry_number_and_ledger_name(self):
        message = str(self.journal_entry.get_delete_message())

        self.assertIn(self.journal_entry.je_number, message)
        self.assertIn(self.ledger_model.name, message)
