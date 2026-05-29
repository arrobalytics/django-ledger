"""
High-level API behavior tests for TransactionModel helper properties and URLs.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.unit import EntityUnitModel


class TransactionHelpersAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_tx_helpers_admin",
            email="api-tx-helpers-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_setup(self, *, name="API Transaction Helpers Entity"):
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

        return {
            "cash_account": cash_account,
            "coa_model": coa_model,
            "entity_model": entity_model,
            "expense_account": expense_account,
            "ledger_model": ledger_model,
        }

    def create_unit(self, setup):
        unit_model = EntityUnitModel.add_root(
            name="API Transaction Helpers Unit",
            slug="api-transaction-helpers-unit",
            entity=setup["entity_model"],
            document_prefix="THU",
            active=True,
            hidden=False,
        )
        unit_model.refresh_from_db()
        return unit_model

    def create_journal_entry(self, setup, *, entity_unit=None):
        return JournalEntryModel.objects.create(
            ledger=setup["ledger_model"],
            entity_unit=entity_unit,
            timestamp=self.make_timestamp(),
            description="API Transaction Helpers Journal Entry",
        )

    def create_transaction(
        self,
        journal_entry,
        *,
        account,
        tx_type=TransactionModel.DEBIT,
        amount=Decimal("10.00"),
        description="API Transaction Helpers Transaction",
    ):
        return TransactionModel.objects.create(
            tx_type=tx_type,
            journal_entry=journal_entry,
            account=account,
            amount=amount,
            description=description,
        )

    def test_with_annotated_details_exposes_unit_account_and_timestamp_fields(self):
        setup = self.create_entity_setup(name="API TX Annotated Details Entity")
        unit_model = self.create_unit(setup)
        journal_entry = self.create_journal_entry(setup, entity_unit=unit_model)
        transaction_model = self.create_transaction(
            journal_entry,
            account=setup["expense_account"],
            description="API TX Annotated Details",
        )

        annotated_transaction = TransactionModel.objects.with_annotated_details().get(
            uuid=transaction_model.uuid,
        )

        self.assertEqual(unit_model.name, annotated_transaction.entity_unit_name)
        self.assertEqual(setup["expense_account"].code, annotated_transaction.account_code)
        self.assertEqual(setup["expense_account"].name, annotated_transaction.account_name)
        self.assertEqual(journal_entry.timestamp, annotated_transaction.timestamp)

    def test_manager_annotations_and_plain_instance_fallbacks_expose_related_identifiers(self):
        setup = self.create_entity_setup(name="API TX Helper Property Entity")
        journal_entry = self.create_journal_entry(setup)
        transaction_model = self.create_transaction(
            journal_entry,
            account=setup["expense_account"],
            description="API TX Helper Property",
        )

        annotated_transaction = TransactionModel.objects.get(uuid=transaction_model.uuid)
        plain_transaction = TransactionModel(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=setup["expense_account"],
            amount=Decimal("10.00"),
            description="API TX Plain Helper Property",
        )

        self.assertEqual(setup["entity_model"].slug, annotated_transaction.entity_slug)
        self.assertEqual(setup["ledger_model"].uuid, annotated_transaction.ledger_uuid)
        self.assertEqual(setup["coa_model"].uuid, annotated_transaction.coa_id)

        self.assertEqual(setup["entity_model"].slug, plain_transaction.entity_slug)
        self.assertEqual(setup["ledger_model"].uuid, plain_transaction.ledger_uuid)
        self.assertEqual(setup["coa_model"].uuid, plain_transaction.coa_id)

    def test_type_helpers_identify_debits_and_credits(self):
        setup = self.create_entity_setup(name="API TX Type Helper Entity")
        journal_entry = self.create_journal_entry(setup)
        debit_transaction = self.create_transaction(
            journal_entry,
            account=setup["expense_account"],
            tx_type=TransactionModel.DEBIT,
            description="API TX Debit Helper",
        )
        credit_transaction = self.create_transaction(
            journal_entry,
            account=setup["cash_account"],
            tx_type=TransactionModel.CREDIT,
            description="API TX Credit Helper",
        )

        self.assertTrue(debit_transaction.is_debit())
        self.assertFalse(debit_transaction.is_credit())
        self.assertTrue(credit_transaction.is_credit())
        self.assertFalse(credit_transaction.is_debit())

    def test_url_helpers_return_entity_ledger_and_journal_entry_scoped_urls(self):
        setup = self.create_entity_setup(name="API TX URL Helper Entity")
        journal_entry = self.create_journal_entry(setup)
        transaction_model = self.create_transaction(
            journal_entry,
            account=setup["expense_account"],
            description="API TX URL Helper",
        )

        ledger_url = transaction_model.get_ledger_detailr_url()
        journal_entry_url = transaction_model.get_journal_entry_detail_url()

        self.assertIsInstance(ledger_url, str)
        self.assertIn(setup["entity_model"].slug, ledger_url)
        self.assertIn(str(setup["ledger_model"].uuid), ledger_url)

        self.assertIsInstance(journal_entry_url, str)
        self.assertIn(setup["entity_model"].slug, journal_entry_url)
        self.assertIn(str(setup["ledger_model"].uuid), journal_entry_url)
        self.assertIn(str(journal_entry.uuid), journal_entry_url)

    def test_string_representation_includes_account_and_transaction_details(self):
        setup = self.create_entity_setup(name="API TX String Helper Entity")
        journal_entry = self.create_journal_entry(setup)
        transaction_model = self.create_transaction(
            journal_entry,
            account=setup["expense_account"],
            tx_type=TransactionModel.DEBIT,
            amount=Decimal("42.50"),
            description="API TX String Helper",
        )
        tx_string = str(transaction_model)

        self.assertIn(setup["expense_account"].code, tx_string)
        self.assertIn(setup["expense_account"].name, tx_string)
        self.assertIn(setup["expense_account"].balance_type, tx_string)
        self.assertIn("42.50", tx_string)
        self.assertIn(TransactionModel.DEBIT, tx_string)
