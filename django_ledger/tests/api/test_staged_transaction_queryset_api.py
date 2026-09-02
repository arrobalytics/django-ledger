"""
High-level API behavior tests for StagedTransactionModel queryset helpers.

These tests cover staged transaction scoping and public queryset filters without
exercising migration, matching internals, split commit, receipt, or undo flows.
"""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, CREDIT, DEBIT
from django_ledger.models import BankAccountModel, JournalEntryModel, TransactionModel
from django_ledger.models.data_import import (
    ImportJobModel,
    StagedTransactionModel,
    StagedTransactionModelValidationError,
)
from django_ledger.models.entity import EntityModel


class StagedTransactionQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_staged_transaction_queryset_admin",
            email="api-staged-transaction-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_staged_transaction_queryset_other_admin",
            email="api-staged-transaction-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_setup(
        self,
        *,
        name="API Staged Transaction QuerySet Entity",
        admin=None,
    ):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=admin or self.admin_user,
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
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        income_account = coa_model.create_account(
            code="4010",
            name=f"{name} Income Account",
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
            hidden=False,
        )
        bank_account.configure(
            entity_slug=entity_model,
            user_model=admin or self.admin_user,
            commit=True,
        )
        bank_account.refresh_from_db()
        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "income_account": income_account,
            "bank_account": bank_account,
        }

    def create_import_job(self, setup, *, description="API Staged Transaction QuerySet Job"):
        import_job = ImportJobModel.objects.create(
            description=description,
            bank_account_model=setup["bank_account"],
        )
        import_job.configure(commit=True)
        import_job.refresh_from_db()
        return import_job

    def create_staged_transaction(
        self,
        import_job,
        *,
        fit_id,
        amount="125.00",
        account_model=None,
        parent=None,
        amount_split=None,
        transaction_model=None,
        matched_transaction_model=None,
        matched_transaction=False,
        bundle_split=True,
    ):
        return StagedTransactionModel.objects.create(
            import_job=import_job,
            parent=parent,
            fit_id=fit_id,
            date_posted=date(2026, 1, 15),
            amount=None if parent else Decimal(amount),
            amount_split=amount_split,
            name=f"API Staged Transaction {fit_id}",
            memo=f"API staged transaction memo {fit_id}",
            account_model=account_model,
            transaction_model=transaction_model,
            matched_transaction_model=matched_transaction_model,
            matched_transaction=matched_transaction,
            bundle_split=bundle_split,
        )

    def create_transaction(self, import_job, account_model, *, amount="125.00"):
        journal_entry = JournalEntryModel.objects.create(
            ledger=import_job.ledger_model,
            timestamp=self.make_timestamp(),
            description="API Staged Transaction QuerySet Journal Entry",
        )
        return TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=account_model,
            amount=Decimal(amount),
            description="API staged transaction linked transaction.",
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API Staged Transaction Entity Scope A")
        other_setup = self.create_entity_setup(
            name="API Staged Transaction Entity Scope B",
            admin=self.other_admin_user,
        )
        import_job = self.create_import_job(setup, description="API Staged Job A")
        other_import_job = self.create_import_job(
            other_setup,
            description="API Staged Job B",
        )
        staged_tx = self.create_staged_transaction(import_job, fit_id="FIT-ENTITY-A")
        other_staged_tx = self.create_staged_transaction(
            other_import_job,
            fit_id="FIT-ENTITY-B",
        )
        entity_model = setup["entity_model"]

        for entity_lookup in (entity_model, entity_model.slug, entity_model.uuid):
            with self.subTest(entity_lookup=entity_lookup):
                staged_tx_qs = StagedTransactionModel.objects.for_entity(entity_lookup)

                self.assertTrue(staged_tx_qs.filter(uuid=staged_tx.uuid).exists())
                self.assertFalse(
                    staged_tx_qs.filter(uuid=other_staged_tx.uuid).exists()
                )

    def test_for_entity_rejects_invalid_input(self):
        with self.assertRaises(StagedTransactionModelValidationError):
            StagedTransactionModel.objects.for_entity(object())

    def test_for_import_job_accepts_model_and_uuid(self):
        setup = self.create_entity_setup(name="API Staged Transaction Job Scope Entity")
        import_job = self.create_import_job(setup, description="API Staged Job One")
        other_import_job = self.create_import_job(
            setup,
            description="API Staged Job Two",
        )
        staged_tx = self.create_staged_transaction(import_job, fit_id="FIT-JOB-A")
        other_staged_tx = self.create_staged_transaction(
            other_import_job,
            fit_id="FIT-JOB-B",
        )

        for import_job_lookup in (import_job, import_job.uuid):
            with self.subTest(import_job_lookup=import_job_lookup):
                staged_tx_qs = StagedTransactionModel.objects.for_import_job(
                    import_job_lookup,
                )

                self.assertTrue(staged_tx_qs.filter(uuid=staged_tx.uuid).exists())
                self.assertFalse(
                    staged_tx_qs.filter(uuid=other_staged_tx.uuid).exists()
                )

    def test_for_import_job_rejects_invalid_input(self):
        with self.assertRaises(StagedTransactionModelValidationError):
            StagedTransactionModel.objects.for_import_job(object())

    def test_pending_and_imported_filters_reflect_transaction_links_and_matches(self):
        setup = self.create_entity_setup(name="API Staged Transaction Pending Entity")
        import_job = self.create_import_job(setup)
        pending_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-PENDING",
        )
        linked_transaction = self.create_transaction(
            import_job,
            setup["cash_account"],
        )
        imported_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-IMPORTED",
            transaction_model=linked_transaction,
        )

        staged_tx_qs = StagedTransactionModel.objects.for_import_job(import_job)
        pending_qs = staged_tx_qs.is_pending()
        imported_qs = staged_tx_qs.is_imported()

        self.assertTrue(pending_qs.filter(uuid=pending_tx.uuid).exists())
        self.assertFalse(pending_qs.filter(uuid=imported_tx.uuid).exists())

        self.assertTrue(imported_qs.filter(uuid=imported_tx.uuid).exists())
        self.assertFalse(imported_qs.filter(uuid=pending_tx.uuid).exists())

    def test_parent_filter_returns_only_parent_rows(self):
        setup = self.create_entity_setup(name="API Staged Transaction Parent Entity")
        import_job = self.create_import_job(setup)
        parent_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-PARENT",
        )
        child_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-PARENT",
            parent=parent_tx,
            amount_split=Decimal("50.00"),
        )

        parent_qs = StagedTransactionModel.objects.for_import_job(import_job).is_parent()

        self.assertTrue(parent_qs.filter(uuid=parent_tx.uuid).exists())
        self.assertFalse(parent_qs.filter(uuid=child_tx.uuid).exists())

    def test_ready_filters_return_ready_to_import_and_ready_to_match_rows(self):
        setup = self.create_entity_setup(name="API Staged Transaction Ready Entity")
        import_job = self.create_import_job(setup)
        ready_to_import_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-READY-IMPORT",
            account_model=setup["income_account"],
        )
        not_ready_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-NOT-READY",
        )
        matched_transaction = self.create_transaction(
            import_job,
            setup["cash_account"],
        )
        ready_to_match_tx = self.create_staged_transaction(
            import_job,
            fit_id="FIT-READY-MATCH",
            matched_transaction_model=matched_transaction,
            matched_transaction=False,
        )

        staged_tx_qs = StagedTransactionModel.objects.for_import_job(import_job)
        ready_to_import_qs = staged_tx_qs.is_ready_to_import()
        ready_to_match_qs = staged_tx_qs.is_ready_to_match()

        self.assertTrue(
            ready_to_import_qs.filter(uuid=ready_to_import_tx.uuid).exists()
        )
        self.assertFalse(ready_to_import_qs.filter(uuid=not_ready_tx.uuid).exists())
        self.assertFalse(
            ready_to_import_qs.filter(uuid=ready_to_match_tx.uuid).exists()
        )

        self.assertTrue(ready_to_match_qs.filter(uuid=ready_to_match_tx.uuid).exists())
        self.assertFalse(ready_to_match_qs.filter(uuid=ready_to_import_tx.uuid).exists())
        self.assertFalse(ready_to_match_qs.filter(uuid=not_ready_tx.uuid).exists())
