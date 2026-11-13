"""
High-level API tests for ClosingEntryModel delete and helper URLs.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import TransactionModel
from django_ledger.models.closing_entry import (
    ClosingEntryModel,
    ClosingEntryTransactionModel,
    ClosingEntryValidationError,
)
from django_ledger.models.entity import EntityModel


class ClosingEntryDeleteURLAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_closing_entry_delete_url_user",
            email="api-closing-entry-delete-url-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Closing Entry Delete URL Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        cash_account = coa_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        equity_account = coa_model.create_account(
            code="3010",
            name=f"{name} Equity Account",
            role="eq_capital",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
            "equity_account": equity_account,
        }

    def create_closing_entry(self, setup, *, closing_date=date(2025, 12, 31)):
        closing_entry = ClosingEntryModel.objects.create(
            entity_model=setup["entity_model"],
            closing_date=closing_date,
        )
        closing_entry.refresh_from_db()
        return closing_entry

    def create_balanced_closing_transactions(self, closing_entry, setup):
        debit_tx = ClosingEntryTransactionModel.objects.create(
            closing_entry_model=closing_entry,
            account_model=setup["cash_account"],
            tx_type=TransactionModel.DEBIT,
            balance=Decimal("100.00"),
        )
        credit_tx = ClosingEntryTransactionModel.objects.create(
            closing_entry_model=closing_entry,
            account_model=setup["equity_account"],
            tx_type=TransactionModel.CREDIT,
            balance=Decimal("100.00"),
        )
        return debit_tx, credit_tx

    def test_unposted_closing_entry_can_be_deleted_and_removes_related_ledger_state(self):
        setup = self.create_entity_setup()
        closing_entry = self.create_closing_entry(setup)
        debit_tx, credit_tx = self.create_balanced_closing_transactions(closing_entry, setup)
        ledger_model = closing_entry.ledger_model

        self.assertTrue(closing_entry.can_delete())

        closing_entry.delete()

        self.assertFalse(ClosingEntryModel.objects.filter(uuid=closing_entry.uuid).exists())
        self.assertFalse(ClosingEntryTransactionModel.objects.filter(uuid__in=[debit_tx.uuid, credit_tx.uuid]).exists())
        self.assertFalse(ledger_model.__class__.objects.filter(uuid=ledger_model.uuid).exists())

    def test_posted_closing_entry_rejects_delete_and_leaves_state_intact(self):
        setup = self.create_entity_setup(name="API Closing Entry Delete Posted Entity")
        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_transactions(closing_entry, setup)
        closing_entry.mark_as_posted(commit=True, update_entity_meta=False)
        closing_entry.refresh_from_db()

        with self.assertRaises(ClosingEntryValidationError):
            closing_entry.delete()

        persisted_closing_entry = ClosingEntryModel.objects.get(uuid=closing_entry.uuid)
        self.assertTrue(persisted_closing_entry.posted)
        self.assertTrue(persisted_closing_entry.ledger_model.locked)

    def test_url_helpers_return_entity_scoped_strings(self):
        setup = self.create_entity_setup(name="API Closing Entry URL Entity")
        closing_entry = self.create_closing_entry(setup)
        entity_slug = setup["entity_model"].slug
        closing_entry_uuid = str(closing_entry.uuid)

        helper_names = [
            "get_mark_as_posted_url",
            "get_mark_as_unposted_url",
            "get_update_transactions_url",
            "get_delete_url",
        ]

        for helper_name in helper_names:
            with self.subTest(helper_name=helper_name):
                url = getattr(closing_entry, helper_name)()
                self.assertIsInstance(url, str)
                self.assertTrue(url)
                self.assertIn(entity_slug, url)
                self.assertIn(closing_entry_uuid, url)

        list_url = closing_entry.get_list_url()
        self.assertIsInstance(list_url, str)
        self.assertTrue(list_url)
        self.assertIn(entity_slug, list_url)
        self.assertNotIn(closing_entry_uuid, list_url)

    def test_message_and_html_id_helpers_return_non_empty_strings(self):
        setup = self.create_entity_setup(name="API Closing Entry Message Entity")
        closing_entry = self.create_closing_entry(setup)

        helper_names = [
            "get_mark_as_posted_html_id",
            "get_mark_as_unposted_html_id",
            "get_update_transactions_html_id",
            "get_delete_html_id",
            "get_html_id",
        ]

        for helper_name in helper_names:
            with self.subTest(helper_name=helper_name):
                value = str(getattr(closing_entry, helper_name)())
                self.assertTrue(value)
                self.assertIn(str(closing_entry.uuid), value)

        message_helper_names = [
            "get_mark_as_posted_message",
            "get_mark_as_unposted_message",
            "get_update_transactions_message",
            "get_delete_message",
        ]

        for helper_name in message_helper_names:
            with self.subTest(helper_name=helper_name):
                value = str(getattr(closing_entry, helper_name)())
                self.assertTrue(value)
                self.assertIn(str(closing_entry.closing_date), value)
