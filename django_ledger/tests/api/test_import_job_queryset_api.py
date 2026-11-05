"""
High-level API behavior tests for ImportJobModel queryset helpers.

These tests cover entity/user scoping and manager annotations without
exercising staged transaction migration, matching, receipts, or undo flows.
"""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT
from django_ledger.models import BankAccountModel, JournalEntryModel, TransactionModel
from django_ledger.models.data_import import (
    ImportJobModel,
    ImportJobModelValidationError,
    StagedTransactionModel,
)
from django_ledger.models.entity import EntityManagementModel, EntityModel


class ImportJobQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_import_job_queryset_admin",
            email="api-import-job-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_import_job_queryset_other_admin",
            email="api-import-job-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_import_job_queryset_manager",
            email="api-import-job-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_import_job_queryset_unrelated",
            email="api-import-job-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_import_job_queryset_superuser",
            email="api-import-job-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_setup(
        self,
        *,
        name="API Import Job QuerySet Entity",
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
            "bank_account": bank_account,
        }

    def create_import_job(self, setup, *, description="API Import Job QuerySet Job"):
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
        transaction_model=None,
    ):
        return StagedTransactionModel.objects.create(
            import_job=import_job,
            fit_id=fit_id,
            date_posted=date(2026, 1, 15),
            amount=Decimal(amount),
            name=f"API Staged Transaction {fit_id}",
            memo=f"API staged transaction memo {fit_id}",
            transaction_model=transaction_model,
        )

    def create_imported_transaction(self, import_job, account_model):
        journal_entry = JournalEntryModel.objects.create(
            ledger=import_job.ledger_model,
            timestamp=self.make_timestamp(),
            description="API Import Job Annotation Journal Entry",
        )
        return TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=account_model,
            amount=Decimal("125.00"),
            description="API imported transaction.",
        )

    def test_for_entity_accepts_entity_model_and_uuid(self):
        setup = self.create_entity_setup(name="API Import Job Entity Scope A")
        other_setup = self.create_entity_setup(
            name="API Import Job Entity Scope B",
            admin=self.other_admin_user,
        )
        import_job = self.create_import_job(setup, description="API Import Job A")
        other_import_job = self.create_import_job(
            other_setup,
            description="API Import Job B",
        )
        entity_model = setup["entity_model"]

        for entity_lookup in (entity_model, entity_model.uuid):
            with self.subTest(entity_lookup=entity_lookup):
                import_job_qs = ImportJobModel.objects.for_entity(entity_lookup)

                self.assertTrue(import_job_qs.filter(uuid=import_job.uuid).exists())
                self.assertFalse(
                    import_job_qs.filter(uuid=other_import_job.uuid).exists()
                )

    def test_for_entity_slug_behavior(self):
        setup = self.create_entity_setup(name="API Import Job Slug Scope A")
        other_setup = self.create_entity_setup(
            name="API Import Job Slug Scope B",
            admin=self.other_admin_user,
        )
        import_job = self.create_import_job(setup, description="API Import Job Slug A")
        other_import_job = self.create_import_job(
            other_setup,
            description="API Import Job Slug B",
        )

        import_job_qs = ImportJobModel.objects.for_entity(setup["entity_model"].slug)

        self.assertTrue(import_job_qs.filter(uuid=import_job.uuid).exists())
        self.assertFalse(import_job_qs.filter(uuid=other_import_job.uuid).exists())

    def test_for_entity_rejects_invalid_input(self):
        with self.assertRaises(ImportJobModelValidationError):
            ImportJobModel.objects.for_entity(object())

    def test_for_user_scopes_import_jobs_by_entity_access(self):
        setup = self.create_entity_setup(name="API Import Job User Scope Entity")
        other_setup = self.create_entity_setup(
            name="API Import Job Other User Scope Entity",
            admin=self.other_admin_user,
        )
        import_job = self.create_import_job(setup, description="API User Scope Job")
        other_import_job = self.create_import_job(
            other_setup,
            description="API Other User Scope Job",
        )

        EntityManagementModel.objects.create(
            entity=setup["entity_model"],
            user=self.manager_user,
            permission_level="read",
        )

        import_job_qs = ImportJobModel.objects.all()
        admin_qs = import_job_qs.for_user(self.admin_user)
        manager_qs = import_job_qs.for_user(self.manager_user)
        unrelated_qs = import_job_qs.for_user(self.unrelated_user)
        superuser_qs = import_job_qs.for_user(self.superuser)

        self.assertTrue(admin_qs.filter(uuid=import_job.uuid).exists())
        self.assertFalse(admin_qs.filter(uuid=other_import_job.uuid).exists())

        self.assertTrue(manager_qs.filter(uuid=import_job.uuid).exists())
        self.assertFalse(manager_qs.filter(uuid=other_import_job.uuid).exists())

        self.assertFalse(unrelated_qs.filter(uuid=import_job.uuid).exists())
        self.assertFalse(unrelated_qs.filter(uuid=other_import_job.uuid).exists())

        self.assertTrue(superuser_qs.filter(uuid=import_job.uuid).exists())
        self.assertTrue(superuser_qs.filter(uuid=other_import_job.uuid).exists())

    def test_manager_annotations_track_pending_and_complete_jobs(self):
        setup = self.create_entity_setup(name="API Import Job Annotation Entity")
        pending_job = self.create_import_job(setup, description="API Pending Import Job")
        complete_job = self.create_import_job(setup, description="API Complete Import Job")
        empty_job = self.create_import_job(setup, description="API Empty Import Job")

        self.create_staged_transaction(
            pending_job,
            fit_id="FIT-PENDING-001",
            amount="125.00",
        )
        imported_transaction = self.create_imported_transaction(
            complete_job,
            setup["cash_account"],
        )
        self.create_staged_transaction(
            complete_job,
            fit_id="FIT-IMPORTED-001",
            amount="125.00",
            transaction_model=imported_transaction,
        )

        annotated_pending_job = ImportJobModel.objects.get(uuid=pending_job.uuid)
        annotated_complete_job = ImportJobModel.objects.get(uuid=complete_job.uuid)
        annotated_empty_job = ImportJobModel.objects.get(uuid=empty_job.uuid)

        self.assertEqual(annotated_pending_job.txs_count, 1)
        self.assertEqual(annotated_pending_job.txs_imported_count, 0)
        self.assertEqual(annotated_pending_job.txs_pending, 1)
        self.assertFalse(annotated_pending_job.is_complete)

        self.assertEqual(annotated_complete_job.txs_count, 1)
        self.assertEqual(annotated_complete_job.txs_imported_count, 1)
        self.assertEqual(annotated_complete_job.txs_pending, 0)
        self.assertTrue(annotated_complete_job.is_complete)

        self.assertEqual(annotated_empty_job.txs_count, 0)
        self.assertEqual(annotated_empty_job.txs_imported_count, 0)
        self.assertEqual(annotated_empty_job.txs_pending, 0)
        self.assertFalse(annotated_empty_job.is_complete)
