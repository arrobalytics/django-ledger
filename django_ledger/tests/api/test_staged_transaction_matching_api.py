"""
High-level API tests for StagedTransactionModel matching helpers.

These tests cover candidate discovery and match/unmatch state without testing a
full reconciliation workflow.
"""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, CREDIT, DEBIT
from django_ledger.models import BankAccountModel, JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.data_import import (
    ImportJobModel,
    StagedTransactionModel,
    StagedTransactionModelValidationError,
)
from django_ledger.models.entity import EntityModel
from django_ledger.models.receipt import ReceiptModel


class StagedTransactionMatchingAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_staged_matching_admin",
            email="api-staged-matching-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self, year=2026, month=1, day=15):
        if settings.USE_TZ:
            return datetime(year, month, day, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(year, month, day, 12, 0)

    def create_entity_setup(self, *, name="API Staged Matching Entity"):
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
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        income_account = coa_model.create_account(
            code="4010",
            name=f"{name} Income",
            role="in_operational",
            balance_type=CREDIT,
            active=True,
        )
        bank_account = BankAccountModel(
            name=f"{name} Bank Account",
            account_model=cash_account,
            account_number="000123456789",
            routing_number="000111000",
            active=True,
        )
        bank_account.configure(entity_slug=entity_model, user_model=self.admin_user, commit=True)
        import_job = ImportJobModel.objects.create(
            description=f"{name} Import Job",
            bank_account_model=bank_account,
        )
        import_job.configure(commit=True)
        import_job.refresh_from_db()
        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
            "income_account": income_account,
            "bank_account": bank_account,
            "import_job": import_job,
        }

    def create_posted_transaction(
        self,
        setup,
        *,
        account,
        amount="125.00",
        timestamp=None,
        posted=True,
    ):
        ledger_model = LedgerModel.objects.create(
            name="API Staged Matching Candidate Ledger",
            entity=setup["entity_model"],
            posted=posted,
        )
        journal_entry = JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=timestamp or self.make_timestamp(),
            description="API Staged Matching Candidate Journal Entry",
        )
        transaction_model = TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=account,
            amount=Decimal(amount),
            description="API staged matching candidate transaction.",
        )
        if posted:
            JournalEntryModel.objects.filter(uuid=journal_entry.uuid).update(posted=True)
            journal_entry.refresh_from_db()
        return transaction_model

    def create_staged_transaction(
        self,
        setup,
        *,
        fit_id="FIT-MATCH",
        amount="125.00",
        receipt_type=ReceiptModel.TRANSFER_RECEIPT,
        matched_transaction_model=None,
        matched_transaction=False,
    ):
        staged_tx = StagedTransactionModel.objects.create(
            import_job=setup["import_job"],
            fit_id=fit_id,
            date_posted=date(2026, 1, 15),
            amount=Decimal(amount),
            name=f"API Staged Transaction {fit_id}",
            memo=f"API staged transaction memo {fit_id}",
            receipt_type=receipt_type,
            matched_transaction_model=matched_transaction_model,
            matched_transaction=matched_transaction,
        )
        return StagedTransactionModel.objects.get(uuid=staged_tx.uuid)

    def test_get_match_candidates_returns_posted_same_account_same_amount_within_window(self):
        setup = self.create_entity_setup()
        candidate_tx = self.create_posted_transaction(
            setup,
            account=setup["cash_account"],
            amount="125.00",
            timestamp=self.make_timestamp(2026, 1, 16),
        )
        staged_tx = self.create_staged_transaction(setup)

        candidate_qs = staged_tx.get_match_candidates_qs()

        self.assertTrue(candidate_qs.filter(uuid=candidate_tx.uuid).exists())

    def test_get_match_candidates_excludes_unposted_wrong_account_wrong_amount_or_outside_window(self):
        setup = self.create_entity_setup()
        matching_tx = self.create_posted_transaction(
            setup,
            account=setup["cash_account"],
            amount="125.00",
        )
        unposted_tx = self.create_posted_transaction(
            setup,
            account=setup["cash_account"],
            amount="125.00",
            posted=False,
        )
        wrong_account_tx = self.create_posted_transaction(
            setup,
            account=setup["income_account"],
            amount="125.00",
        )
        wrong_amount_tx = self.create_posted_transaction(
            setup,
            account=setup["cash_account"],
            amount="126.00",
        )
        outside_window_tx = self.create_posted_transaction(
            setup,
            account=setup["cash_account"],
            amount="125.00",
            timestamp=self.make_timestamp(2026, 1, 25),
        )
        staged_tx = self.create_staged_transaction(setup)
        candidate_ids = set(staged_tx.get_match_candidates_qs().values_list("uuid", flat=True))

        self.assertIn(matching_tx.uuid, candidate_ids)
        self.assertNotIn(unposted_tx.uuid, candidate_ids)
        self.assertNotIn(wrong_account_tx.uuid, candidate_ids)
        self.assertNotIn(wrong_amount_tx.uuid, candidate_ids)
        self.assertNotIn(outside_window_tx.uuid, candidate_ids)

    def test_can_match_and_ready_to_match_reflect_candidate_state(self):
        setup = self.create_entity_setup()
        candidate_tx = self.create_posted_transaction(
            setup,
            account=setup["cash_account"],
            amount="125.00",
        )
        staged_tx = self.create_staged_transaction(
            setup,
            matched_transaction_model=candidate_tx,
            matched_transaction=False,
        )

        self.assertTrue(staged_tx.can_match())
        self.assertFalse(staged_tx.can_unmatch())
        self.assertTrue(
            StagedTransactionModel.objects.is_ready_to_match()
            .filter(uuid=staged_tx.uuid)
            .exists()
        )

    def test_can_unmatch_and_unmatch_clear_match_state(self):
        setup = self.create_entity_setup()
        candidate_tx = self.create_posted_transaction(
            setup,
            account=setup["cash_account"],
            amount="125.00",
        )
        staged_tx = self.create_staged_transaction(
            setup,
            matched_transaction_model=candidate_tx,
            matched_transaction=True,
        )

        self.assertTrue(staged_tx.can_unmatch())
        self.assertTrue(staged_tx.has_match())

        staged_tx.unmatch(commit=True)
        staged_tx.refresh_from_db()

        self.assertFalse(staged_tx.matched_transaction)
        self.assertIsNone(staged_tx.matched_transaction_model_id)
        self.assertFalse(staged_tx.has_match())

    def test_unmatch_rejects_unmatched_transaction_by_default(self):
        setup = self.create_entity_setup()
        staged_tx = self.create_staged_transaction(setup)

        with self.assertRaises(StagedTransactionModelValidationError):
            staged_tx.unmatch()
