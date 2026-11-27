"""
High-level API behavior tests for JournalEntryModel verify, clean, and save.

These tests cover verification and save-time verification flows without
exercising lifecycle signals or detailed activity classification.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.journal_entry import JournalEntryValidationError


class JournalEntryVerifyAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_je_verify_admin",
            email="api-je-verify-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self, *, year=2026, month=1, day=15):
        if settings.USE_TZ:
            return datetime(year, month, day, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(year, month, day, 12, 0)

    def create_entity_with_accounting_setup(self, *, name="API JE Verify Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
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
            name=f"{name} Cash",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense",
            role="ex_regular",
            balance_type="debit",
            active=True,
        )
        ledger_model = LedgerModel.objects.create(
            name=f"{name} Ledger",
            ledger_xid=f"{name.lower().replace(' ', '-')}-ledger",
            entity=entity_model,
        )
        journal_entry = JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=self.make_timestamp(),
            description=f"{name} Journal Entry",
        )

        return {
            "cash_account": cash_account,
            "expense_account": expense_account,
            "ledger_model": ledger_model,
            "journal_entry": journal_entry,
        }

    def create_journal_entry(
        self,
        ledger_model,
        *,
        description="API JE Verify Journal Entry",
        timestamp=None,
        posted=False,
        force_create=False,
    ):
        create_kwargs = {
            "ledger": ledger_model,
            "timestamp": timestamp or self.make_timestamp(),
            "description": description,
            "posted": posted,
        }
        if force_create:
            create_kwargs["force_create"] = True
        return JournalEntryModel.objects.create(**create_kwargs)

    def add_transactions(
        self,
        journal_entry,
        *,
        debit_account,
        credit_account,
        debit_amount=Decimal("100.00"),
        credit_amount=Decimal("100.00"),
    ):
        debit_tx = TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=debit_account,
            amount=debit_amount,
            description="Verify debit.",
        )
        credit_tx = TransactionModel.objects.create(
            tx_type=TransactionModel.CREDIT,
            journal_entry=journal_entry,
            account=credit_account,
            amount=credit_amount,
            description="Verify credit.",
        )
        return debit_tx, credit_tx

    def create_balanced_journal_entry(self, setup, *, description="API JE Verify Balanced"):
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description=description,
        )
        self.add_transactions(
            journal_entry,
            debit_account=setup["expense_account"],
            credit_account=setup["cash_account"],
        )
        return journal_entry

    def create_imbalanced_journal_entry(self, setup, *, description="API JE Verify Imbalanced"):
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description=description,
        )
        self.add_transactions(
            journal_entry,
            debit_account=setup["expense_account"],
            credit_account=setup["cash_account"],
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("90.00"),
        )
        return journal_entry

    def test_verify_marks_balanced_entry_verified_and_returns_transactions(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Verify Balanced Entity",
        )
        journal_entry = self.create_balanced_journal_entry(setup)

        txs_qs, verified = journal_entry.verify()

        self.assertEqual(2, txs_qs.count())
        self.assertTrue(verified)
        self.assertTrue(journal_entry.is_verified())
        self.assertTrue(journal_entry.has_activity())

    def test_verify_force_verify_revalidates_after_entry_was_already_verified(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Force Verify Entity",
        )
        journal_entry = self.create_balanced_journal_entry(setup)
        journal_entry.verify()
        credit_tx = journal_entry.get_transaction_queryset().get(tx_type=TransactionModel.CREDIT)
        credit_tx.amount = Decimal("90.00")
        credit_tx.save()

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.verify(force_verify=True)

    def test_verify_raises_for_imbalanced_transactions(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Verify Imbalanced Entity",
        )
        journal_entry = self.create_imbalanced_journal_entry(setup)

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.verify()

    def test_clean_without_verify_returns_transactions_and_current_verified_state(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Clean No Verify Entity",
        )
        journal_entry = self.create_balanced_journal_entry(setup)

        txs_qs, verified = journal_entry.clean(verify=False)

        self.assertTrue(journal_entry.je_number)
        self.assertEqual(2, txs_qs.count())
        self.assertFalse(verified)
        self.assertFalse(journal_entry.is_verified())

    def test_clean_with_verify_verifies_balanced_entry(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Clean Verify Entity",
        )
        journal_entry = self.create_balanced_journal_entry(setup)

        txs_qs, verified = journal_entry.clean(verify=True)

        self.assertEqual(2, txs_qs.count())
        self.assertTrue(verified)
        self.assertTrue(journal_entry.is_verified())

    def test_clean_rejects_posted_entry_with_future_timestamp(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Clean Future Posted Entity",
        )
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description="API JE Future Posted",
            timestamp=self.make_timestamp(year=2099),
            posted=True,
            force_create=True,
        )

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.clean()

    def test_save_verify_false_allows_saving_unverified_entry(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Save No Verify Entity",
        )
        journal_entry = setup["journal_entry"]
        journal_entry.description = "API JE Save No Verify Updated"

        journal_entry.save(verify=False)

        journal_entry.refresh_from_db()
        self.assertEqual("API JE Save No Verify Updated", journal_entry.description)

    def test_save_verify_true_rejects_invalid_entry(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Save Verify Invalid Entity",
        )
        journal_entry = self.create_imbalanced_journal_entry(setup)
        journal_entry.description = "API JE Save Verify Invalid Updated"

        with self.assertRaises(JournalEntryValidationError):
            journal_entry.save(verify=True)

    def test_save_post_on_verify_posts_and_locks_balanced_entry(self):
        setup = self.create_entity_with_accounting_setup(
            name="API JE Save Post On Verify Entity",
        )
        journal_entry = self.create_balanced_journal_entry(setup)

        journal_entry.save(verify=True, post_on_verify=True)

        journal_entry.refresh_from_db()
        self.assertTrue(journal_entry.posted)
        self.assertTrue(journal_entry.locked)
        self.assertTrue(journal_entry.activity)
