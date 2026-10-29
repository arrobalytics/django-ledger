"""
High-level API behavior tests for ImportJobModel helpers.

These tests cover import job configuration, display, URL, and validation
behavior without exercising staged transaction migration or matching flows.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT
from django_ledger.models import BankAccountModel, LedgerModel
from django_ledger.models.data_import import (
    ImportJobModel,
    ImportJobModelValidationError,
)
from django_ledger.models.entity import EntityModel


class ImportJobHelpersAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_import_job_helpers_admin",
            email="api-import-job-helpers-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_import_job_helpers_other_admin",
            email="api-import-job-helpers-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(
        self,
        *,
        name="API Import Job Helpers Entity",
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

    def create_unconfigured_import_job(
        self,
        setup,
        *,
        description="API Import Job Helpers Job",
    ):
        return ImportJobModel.objects.create(
            description=description,
            bank_account_model=setup["bank_account"],
        )

    def create_configured_import_job(
        self,
        setup,
        *,
        description="API Import Job Helpers Job",
    ):
        import_job = self.create_unconfigured_import_job(
            setup,
            description=description,
        )
        import_job.configure(commit=True)
        import_job.refresh_from_db()
        return import_job

    def test_configure_commit_false_creates_in_memory_ledger_without_persisting_binding(self):
        setup = self.create_entity_setup(name="API Import Job Commit False Entity")
        import_job = self.create_unconfigured_import_job(
            setup,
            description="API Import Job Commit False",
        )

        import_job.configure(commit=False)

        self.assertTrue(import_job.is_configured())
        self.assertIsNotNone(import_job.ledger_model_id)
        self.assertEqual(import_job.ledger_model.entity_id, setup["entity_model"].uuid)
        self.assertTrue(
            LedgerModel.objects.filter(uuid=import_job.ledger_model_id).exists()
        )

        persisted_import_job = ImportJobModel._base_manager.get(uuid=import_job.uuid)
        self.assertIsNone(persisted_import_job.ledger_model_id)

    def test_configure_commit_true_persists_ledger_binding(self):
        setup = self.create_entity_setup(name="API Import Job Commit True Entity")
        import_job = self.create_unconfigured_import_job(
            setup,
            description="API Import Job Commit True",
        )

        import_job.configure(commit=True)
        import_job.refresh_from_db()

        self.assertTrue(import_job.is_configured())
        self.assertIsNotNone(import_job.ledger_model_id)
        self.assertEqual(import_job.ledger_model.entity_id, setup["entity_model"].uuid)
        self.assertEqual(
            import_job.bank_account_model.entity_model_id,
            import_job.ledger_model.entity_id,
        )

    def test_presave_rejects_bank_account_and_ledger_from_different_entities(self):
        setup = self.create_entity_setup(name="API Import Job Valid Entity")
        other_setup = self.create_entity_setup(
            name="API Import Job Other Ledger Entity",
            admin=self.other_admin_user,
        )
        other_ledger = other_setup["entity_model"].create_ledger(
            name="API Import Job Mismatched Ledger",
        )

        with self.assertRaises(ImportJobModelValidationError):
            ImportJobModel.objects.create(
                description="API Import Job Mismatched Entity",
                bank_account_model=setup["bank_account"],
                ledger_model=other_ledger,
            )

    def test_entity_slug_and_uuid_use_annotation_and_fallback(self):
        setup = self.create_entity_setup(name="API Import Job Annotation Fallback Entity")
        import_job = self.create_configured_import_job(
            setup,
            description="API Import Job Annotation Fallback",
        )

        annotated_import_job = ImportJobModel.objects.get(uuid=import_job.uuid)
        self.assertEqual(annotated_import_job.entity_slug, setup["entity_model"].slug)
        self.assertEqual(annotated_import_job.entity_uuid, setup["entity_model"].uuid)

        direct_import_job = ImportJobModel(
            description="API Direct Import Job",
            bank_account_model=setup["bank_account"],
            ledger_model=import_job.ledger_model,
        )

        self.assertEqual(direct_import_job.entity_slug, setup["entity_model"].slug)
        self.assertEqual(direct_import_job.entity_uuid, setup["entity_model"].uuid)

    def test_url_helpers_include_entity_slug_and_job_uuid(self):
        setup = self.create_entity_setup(name="API Import Job URL Entity")
        import_job = self.create_configured_import_job(
            setup,
            description="API Import Job URL",
        )
        entity_slug = setup["entity_model"].slug
        job_uuid = str(import_job.uuid)

        job_url_helpers = [
            "get_data_import_url",
            "get_data_import_reset_url",
            "get_absolute_url",
            "get_detail_url",
            "get_update_url",
            "get_delete_url",
            "get_edit_txs_url",
        ]

        for helper_name in job_url_helpers:
            with self.subTest(helper_name=helper_name):
                url = getattr(import_job, helper_name)()

                self.assertIsInstance(url, str)
                self.assertTrue(url)
                self.assertIn(entity_slug, url)
                self.assertIn(job_uuid, url)

        list_url = import_job.get_list_url()
        self.assertIsInstance(list_url, str)
        self.assertTrue(list_url)
        self.assertIn(entity_slug, list_url)
        self.assertNotIn(job_uuid, list_url)

        ledger_url = import_job.get_ledger_detail_url()
        self.assertIsInstance(ledger_url, str)
        self.assertTrue(ledger_url)
        self.assertIn(entity_slug, ledger_url)
        self.assertIn(str(import_job.ledger_model_id), ledger_url)

    def test_str_and_delete_message_include_description(self):
        setup = self.create_entity_setup(name="API Import Job Display Entity")
        import_job = self.create_configured_import_job(
            setup,
            description="API Import Job Display",
        )

        display_value = str(import_job)
        delete_message = str(import_job.get_delete_message())

        self.assertIsInstance(display_value, str)
        self.assertTrue(display_value)
        self.assertIn("API Import Job Display", display_value)

        self.assertIsInstance(delete_message, str)
        self.assertTrue(delete_message)
        self.assertIn("API Import Job Display", delete_message)
