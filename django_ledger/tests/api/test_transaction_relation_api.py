"""
High-level API behavior tests for TransactionModel ledger and journal-entry
relation filters.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityModel


class TransactionRelationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_tx_relation_admin",
            email="api-tx-relation-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_setup(self, *, name="API Transaction Relation Entity"):
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
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense",
            role="ex_regular",
            balance_type="debit",
            active=True,
        )

        return {
            "entity_model": entity_model,
            "expense_account": expense_account,
        }

    def create_ledger(self, entity_model, *, name, ledger_xid):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=ledger_xid,
            entity=entity_model,
        )

    def create_journal_entry(self, ledger_model, *, description):
        return JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=self.make_timestamp(),
            description=description,
        )

    def create_transaction(self, journal_entry, *, account, description):
        return TransactionModel.objects.create(
            tx_type=TransactionModel.DEBIT,
            journal_entry=journal_entry,
            account=account,
            amount=Decimal("10.00"),
            description=description,
        )

    def transaction_ids(self, queryset):
        return set(queryset.values_list("uuid", flat=True))

    def create_two_ledger_setup(self):
        setup = self.create_entity_setup()
        ledger_a = self.create_ledger(
            setup["entity_model"],
            name="API TX Relation Ledger A",
            ledger_xid="api-tx-relation-ledger-a",
        )
        ledger_b = self.create_ledger(
            setup["entity_model"],
            name="API TX Relation Ledger B",
            ledger_xid="api-tx-relation-ledger-b",
        )
        journal_entry_a = self.create_journal_entry(
            ledger_a,
            description="API TX Relation JE A",
        )
        journal_entry_b = self.create_journal_entry(
            ledger_b,
            description="API TX Relation JE B",
        )
        transaction_a = self.create_transaction(
            journal_entry_a,
            account=setup["expense_account"],
            description="API TX Relation Transaction A",
        )
        transaction_b = self.create_transaction(
            journal_entry_b,
            account=setup["expense_account"],
            description="API TX Relation Transaction B",
        )

        return {
            "entity_model": setup["entity_model"],
            "journal_entry_a": journal_entry_a,
            "journal_entry_b": journal_entry_b,
            "ledger_a": ledger_a,
            "ledger_b": ledger_b,
            "transaction_a": transaction_a,
            "transaction_b": transaction_b,
        }

    def test_for_ledger_filters_by_ledger_model_instance(self):
        setup = self.create_two_ledger_setup()

        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_ledger(
            setup["ledger_a"],
        )

        self.assertEqual({setup["transaction_a"].uuid}, self.transaction_ids(transaction_qs))
        self.assertNotIn(setup["transaction_b"].uuid, self.transaction_ids(transaction_qs))

    def test_for_ledger_filters_by_ledger_uuid_object(self):
        setup = self.create_two_ledger_setup()

        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_ledger(
            setup["ledger_a"].uuid,
        )

        self.assertEqual({setup["transaction_a"].uuid}, self.transaction_ids(transaction_qs))
        self.assertNotIn(setup["transaction_b"].uuid, self.transaction_ids(transaction_qs))

    def test_for_journal_entry_filters_by_journal_entry_model_instance(self):
        setup = self.create_two_ledger_setup()

        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_journal_entry(
            setup["journal_entry_a"],
        )

        self.assertEqual({setup["transaction_a"].uuid}, self.transaction_ids(transaction_qs))
        self.assertNotIn(setup["transaction_b"].uuid, self.transaction_ids(transaction_qs))

    def test_for_journal_entry_filters_by_journal_entry_uuid_object(self):
        setup = self.create_two_ledger_setup()

        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_journal_entry(
            setup["journal_entry_a"].uuid,
        )

        self.assertEqual({setup["transaction_a"].uuid}, self.transaction_ids(transaction_qs))
        self.assertNotIn(setup["transaction_b"].uuid, self.transaction_ids(transaction_qs))

    def test_for_journal_entry_filters_by_journal_entry_uuid_string(self):
        setup = self.create_two_ledger_setup()

        transaction_qs = TransactionModel.objects.for_entity(setup["entity_model"]).for_journal_entry(
            str(setup["journal_entry_a"].uuid),
        )

        self.assertEqual({setup["transaction_a"].uuid}, self.transaction_ids(transaction_qs))
        self.assertNotIn(setup["transaction_b"].uuid, self.transaction_ids(transaction_qs))
