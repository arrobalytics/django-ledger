"""
High-level API behavior tests for TransactionModel account, role, unit, and
activity filters.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.journal_entry import JournalEntryModel as JournalEntryModelClass
from django_ledger.models.transactions import TransactionModelValidationError
from django_ledger.models.unit import EntityUnitModel


class TransactionFilterAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_tx_filter_admin",
            email="api-tx-filter-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_setup(self, *, name="API Transaction Filter Entity"):
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
        receivable_account = coa_model.create_account(
            code="1210",
            name=f"{name} Receivable",
            role="asset_ca_recv",
            balance_type="debit",
            active=True,
        )
        ledger_model = LedgerModel.objects.create(
            name=f"{name} Ledger",
            ledger_xid=f"{name.lower().replace(' ', '-')}-ledger",
            entity=entity_model,
        )

        return {
            "cash_account": cash_account,
            "entity_model": entity_model,
            "expense_account": expense_account,
            "ledger_model": ledger_model,
            "receivable_account": receivable_account,
        }

    def create_unit(self, setup, *, name, slug, document_prefix):
        unit_model = EntityUnitModel.add_root(
            name=name,
            slug=slug,
            entity=setup["entity_model"],
            document_prefix=document_prefix,
            active=True,
            hidden=False,
        )
        unit_model.refresh_from_db()
        return unit_model

    def create_journal_entry(
        self,
        ledger_model,
        *,
        description="API Transaction Filter Journal Entry",
        entity_unit=None,
        activity=None,
    ):
        return JournalEntryModel.objects.create(
            ledger=ledger_model,
            entity_unit=entity_unit,
            timestamp=self.make_timestamp(),
            description=description,
            activity=activity,
        )

    def create_transaction(
        self,
        journal_entry,
        *,
        account,
        tx_type=TransactionModel.DEBIT,
        description="API Transaction Filter Transaction",
    ):
        return TransactionModel.objects.create(
            tx_type=tx_type,
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("10.00"),
            description=description,
        )

    def create_transaction_with_account(self, setup, *, account, description):
        journal_entry = self.create_journal_entry(
            setup["ledger_model"],
            description=f"{description} Journal Entry",
        )
        return self.create_transaction(
            journal_entry,
            account=account,
            description=description,
        )

    def transaction_ids(self, queryset):
        return set(queryset.values_list("uuid", flat=True))

    def test_for_accounts_filters_by_account_models(self):
        setup = self.create_entity_setup(name="API TX Account Model Filter Entity")
        cash_tx = self.create_transaction_with_account(
            setup,
            account=setup["cash_account"],
            description="API TX Cash Account Model",
        )
        expense_tx = self.create_transaction_with_account(
            setup,
            account=setup["expense_account"],
            description="API TX Expense Account Model",
        )
        receivable_tx = self.create_transaction_with_account(
            setup,
            account=setup["receivable_account"],
            description="API TX Receivable Account Model",
        )

        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_accounts([
            setup["cash_account"],
            setup["expense_account"],
        ])

        self.assertEqual({cash_tx.uuid, expense_tx.uuid}, self.transaction_ids(transaction_qs))
        self.assertNotIn(receivable_tx.uuid, self.transaction_ids(transaction_qs))

    def test_for_accounts_filters_by_account_uuid_objects(self):
        setup = self.create_entity_setup(name="API TX Account UUID Filter Entity")
        cash_tx = self.create_transaction_with_account(
            setup,
            account=setup["cash_account"],
            description="API TX Cash Account UUID",
        )
        expense_tx = self.create_transaction_with_account(
            setup,
            account=setup["expense_account"],
            description="API TX Expense Account UUID",
        )
        receivable_tx = self.create_transaction_with_account(
            setup,
            account=setup["receivable_account"],
            description="API TX Receivable Account UUID",
        )

        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_accounts([
            setup["cash_account"].uuid,
            setup["expense_account"].uuid,
        ])

        self.assertEqual({cash_tx.uuid, expense_tx.uuid}, self.transaction_ids(transaction_qs))
        self.assertNotIn(receivable_tx.uuid, self.transaction_ids(transaction_qs))

    def test_for_accounts_filters_by_account_code_strings(self):
        setup = self.create_entity_setup(name="API TX Account Code Filter Entity")
        cash_tx = self.create_transaction_with_account(
            setup,
            account=setup["cash_account"],
            description="API TX Cash Account Code",
        )
        expense_tx = self.create_transaction_with_account(
            setup,
            account=setup["expense_account"],
            description="API TX Expense Account Code",
        )
        receivable_tx = self.create_transaction_with_account(
            setup,
            account=setup["receivable_account"],
            description="API TX Receivable Account Code",
        )

        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_accounts([
            setup["cash_account"].code,
            setup["expense_account"].code,
        ])

        self.assertEqual({cash_tx.uuid, expense_tx.uuid}, self.transaction_ids(transaction_qs))
        self.assertNotIn(receivable_tx.uuid, self.transaction_ids(transaction_qs))

    def test_for_accounts_rejects_invalid_input_and_empty_list(self):
        setup = self.create_entity_setup(name="API TX Account Invalid Filter Entity")
        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"])

        for account_list in (object(), [], [object()]):
            with self.subTest(account_list=account_list):
                with self.assertRaises(TransactionModelValidationError):
                    transaction_qs.for_accounts(account_list)

    def test_for_roles_filters_by_single_role_string(self):
        setup = self.create_entity_setup(name="API TX Role String Filter Entity")
        expense_tx = self.create_transaction_with_account(
            setup,
            account=setup["expense_account"],
            description="API TX Expense Role String",
        )
        cash_tx = self.create_transaction_with_account(
            setup,
            account=setup["cash_account"],
            description="API TX Cash Role String",
        )

        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_roles("ex_regular")

        self.assertEqual({expense_tx.uuid}, self.transaction_ids(transaction_qs))
        self.assertNotIn(cash_tx.uuid, self.transaction_ids(transaction_qs))

    def test_for_roles_filters_by_list_and_set_of_roles(self):
        setup = self.create_entity_setup(name="API TX Role Collection Filter Entity")
        expense_tx = self.create_transaction_with_account(
            setup,
            account=setup["expense_account"],
            description="API TX Expense Role Collection",
        )
        cash_tx = self.create_transaction_with_account(
            setup,
            account=setup["cash_account"],
            description="API TX Cash Role Collection",
        )
        receivable_tx = self.create_transaction_with_account(
            setup,
            account=setup["receivable_account"],
            description="API TX Receivable Role Collection",
        )

        expected_ids = {expense_tx.uuid, cash_tx.uuid}
        role_list_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_roles([
            "ex_regular",
            "asset_ca_cash",
        ])
        role_set_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_roles({
            "ex_regular",
            "asset_ca_cash",
        })

        self.assertEqual(expected_ids, self.transaction_ids(role_list_qs))
        self.assertEqual(expected_ids, self.transaction_ids(role_set_qs))
        self.assertNotIn(receivable_tx.uuid, self.transaction_ids(role_list_qs))

    def test_for_unit_filters_by_entity_unit_instance_and_slug(self):
        setup = self.create_entity_setup(name="API TX Unit Filter Entity")
        unit_a = self.create_unit(
            setup,
            name="API TX Unit A",
            slug="api-tx-unit-a",
            document_prefix="TUA",
        )
        unit_b = self.create_unit(
            setup,
            name="API TX Unit B",
            slug="api-tx-unit-b",
            document_prefix="TUB",
        )
        unit_a_je = self.create_journal_entry(
            setup["ledger_model"],
            description="API TX Unit A Journal Entry",
            entity_unit=unit_a,
        )
        unit_b_je = self.create_journal_entry(
            setup["ledger_model"],
            description="API TX Unit B Journal Entry",
            entity_unit=unit_b,
        )
        unit_a_tx = self.create_transaction(
            unit_a_je,
            account=setup["expense_account"],
            description="API TX Unit A",
        )
        unit_b_tx = self.create_transaction(
            unit_b_je,
            account=setup["expense_account"],
            description="API TX Unit B",
        )

        unit_instance_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_unit(unit_a)
        unit_slug_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_unit(unit_a.slug)

        self.assertEqual({unit_a_tx.uuid}, self.transaction_ids(unit_instance_qs))
        self.assertEqual({unit_a_tx.uuid}, self.transaction_ids(unit_slug_qs))
        self.assertNotIn(unit_b_tx.uuid, self.transaction_ids(unit_instance_qs))

    def test_for_activity_filters_by_single_activity_string(self):
        setup = self.create_entity_setup(name="API TX Activity String Filter Entity")
        operating_je = self.create_journal_entry(
            setup["ledger_model"],
            description="API TX Operating Activity JE",
            activity=JournalEntryModelClass.OPERATING_ACTIVITY,
        )
        financing_je = self.create_journal_entry(
            setup["ledger_model"],
            description="API TX Financing Activity JE",
            activity=JournalEntryModelClass.FINANCING_EQUITY,
        )
        operating_tx = self.create_transaction(
            operating_je,
            account=setup["expense_account"],
            description="API TX Operating Activity",
        )
        financing_tx = self.create_transaction(
            financing_je,
            account=setup["cash_account"],
            description="API TX Financing Activity",
        )

        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_activity(
            JournalEntryModelClass.OPERATING_ACTIVITY,
        )

        self.assertEqual({operating_tx.uuid}, self.transaction_ids(transaction_qs))
        self.assertNotIn(financing_tx.uuid, self.transaction_ids(transaction_qs))

    def test_for_activity_filters_by_list_and_set_of_activities(self):
        setup = self.create_entity_setup(name="API TX Activity Collection Filter Entity")
        operating_je = self.create_journal_entry(
            setup["ledger_model"],
            description="API TX Operating Activity Collection JE",
            activity=JournalEntryModelClass.OPERATING_ACTIVITY,
        )
        financing_je = self.create_journal_entry(
            setup["ledger_model"],
            description="API TX Financing Activity Collection JE",
            activity=JournalEntryModelClass.FINANCING_EQUITY,
        )
        investing_je = self.create_journal_entry(
            setup["ledger_model"],
            description="API TX Investing Activity Collection JE",
            activity=JournalEntryModelClass.INVESTING_PPE,
        )
        operating_tx = self.create_transaction(
            operating_je,
            account=setup["expense_account"],
            description="API TX Operating Activity Collection",
        )
        financing_tx = self.create_transaction(
            financing_je,
            account=setup["cash_account"],
            description="API TX Financing Activity Collection",
        )
        investing_tx = self.create_transaction(
            investing_je,
            account=setup["receivable_account"],
            description="API TX Investing Activity Collection",
        )
        expected_ids = {operating_tx.uuid, financing_tx.uuid}

        activity_list_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_activity([
            JournalEntryModelClass.OPERATING_ACTIVITY,
            JournalEntryModelClass.FINANCING_EQUITY,
        ])
        activity_set_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_activity({
            JournalEntryModelClass.OPERATING_ACTIVITY,
            JournalEntryModelClass.FINANCING_EQUITY,
        })

        self.assertEqual(expected_ids, self.transaction_ids(activity_list_qs))
        self.assertEqual(expected_ids, self.transaction_ids(activity_set_qs))
        self.assertNotIn(investing_tx.uuid, self.transaction_ids(activity_list_qs))
