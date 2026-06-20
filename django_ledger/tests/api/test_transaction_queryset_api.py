"""
High-level API behavior tests for TransactionModel manager and queryset helpers.

These tests cover entity/user scoping and posted transaction filtering without
requiring randomized fixtures.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel, TransactionModel
from django_ledger.models.entity import EntityManagementModel, EntityModel
from django_ledger.models.transactions import TransactionModelValidationError


class TransactionQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_tx_queryset_admin",
            email="api-tx-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_tx_queryset_other_admin",
            email="api-tx-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_tx_queryset_manager",
            email="api-tx-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_tx_queryset_unrelated",
            email="api-tx-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_tx_queryset_superuser",
            email="api-tx-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_setup(self, *, name="API Transaction QuerySet Entity", admin=None):
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

        return {
            "cash_account": cash_account,
            "entity_model": entity_model,
            "expense_account": expense_account,
        }

    def create_ledger(
        self,
        entity_model,
        *,
        name="API Transaction QuerySet Ledger",
        ledger_xid="api-transaction-queryset-ledger",
        posted=False,
    ):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=ledger_xid,
            entity=entity_model,
            posted=posted,
        )

    def create_journal_entry(
        self,
        ledger_model,
        *,
        description="API Transaction QuerySet Journal Entry",
        posted=False,
        force_create=False,
    ):
        create_kwargs = {
            "ledger": ledger_model,
            "timestamp": self.make_timestamp(),
            "description": description,
            "posted": posted,
        }
        if force_create:
            create_kwargs["force_create"] = True
        return JournalEntryModel.objects.create(**create_kwargs)

    def create_transaction(
        self,
        journal_entry,
        *,
        account,
        tx_type=TransactionModel.DEBIT,
        amount=Decimal("10.00"),
        description="API Transaction QuerySet Transaction",
    ):
        return TransactionModel.objects.create(
            tx_type=tx_type,
            journal_entry=journal_entry,
            account=account,
            amount=amount,
            description=description,
        )

    def create_transaction_for_entity(
        self,
        setup,
        *,
        ledger_xid,
        posted_ledger=False,
        posted_journal_entry=False,
        description="API Transaction QuerySet Transaction",
    ):
        ledger_model = self.create_ledger(
            setup["entity_model"],
            ledger_xid=ledger_xid,
            posted=posted_ledger,
        )
        journal_entry = self.create_journal_entry(
            ledger_model,
            description=f"{description} Journal Entry",
            posted=False,
        )
        transaction_model = self.create_transaction(
            journal_entry,
            account=setup["expense_account"],
            description=description,
        )
        if posted_journal_entry:
            JournalEntryModel.objects.filter(uuid=journal_entry.uuid).update(posted=True)
        return transaction_model

    def test_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API TX For Entity A")
        other_setup = self.create_entity_setup(
            name="API TX For Entity B",
            admin=self.other_admin_user,
        )
        transaction_model = self.create_transaction_for_entity(
            setup,
            ledger_xid="api-tx-for-entity-a",
            description="API TX For Entity A",
        )
        other_transaction = self.create_transaction_for_entity(
            other_setup,
            ledger_xid="api-tx-for-entity-b",
            description="API TX For Entity B",
        )
        entity_model = setup["entity_model"]

        for entity_lookup in (entity_model, entity_model.slug, entity_model.uuid):
            with self.subTest(entity_lookup=entity_lookup):
                transaction_qs = TransactionModel.objects.for_entity(entity_lookup)

                self.assertTrue(transaction_qs.filter(uuid=transaction_model.uuid).exists())
                self.assertFalse(transaction_qs.filter(uuid=other_transaction.uuid).exists())

    def test_for_entity_rejects_invalid_input(self):
        with self.assertRaises(TransactionModelValidationError):
            TransactionModel.objects.for_entity(object())

    def test_for_user_scopes_transactions_by_entity_access(self):
        setup = self.create_entity_setup(name="API TX User Scope Entity")
        other_setup = self.create_entity_setup(
            name="API TX Other User Scope Entity",
            admin=self.other_admin_user,
        )
        transaction_model = self.create_transaction_for_entity(
            setup,
            ledger_xid="api-tx-user-scope",
            description="API TX User Scope",
        )
        other_transaction = self.create_transaction_for_entity(
            other_setup,
            ledger_xid="api-tx-other-user-scope",
            description="API TX Other User Scope",
        )

        EntityManagementModel.objects.create(
            entity=setup["entity_model"],
            user=self.manager_user,
            permission_level="read",
        )

        admin_qs = TransactionModel.objects.for_user(self.admin_user)
        manager_qs = TransactionModel.objects.for_user(self.manager_user)
        unrelated_qs = TransactionModel.objects.for_user(self.unrelated_user)
        superuser_qs = TransactionModel.objects.for_user(self.superuser)

        self.assertTrue(admin_qs.filter(uuid=transaction_model.uuid).exists())
        self.assertFalse(admin_qs.filter(uuid=other_transaction.uuid).exists())

        self.assertTrue(manager_qs.filter(uuid=transaction_model.uuid).exists())
        self.assertFalse(manager_qs.filter(uuid=other_transaction.uuid).exists())

        self.assertFalse(unrelated_qs.filter(uuid=transaction_model.uuid).exists())
        self.assertFalse(unrelated_qs.filter(uuid=other_transaction.uuid).exists())

        self.assertTrue(superuser_qs.filter(uuid=transaction_model.uuid).exists())
        self.assertTrue(superuser_qs.filter(uuid=other_transaction.uuid).exists())

    def test_posted_returns_only_transactions_with_posted_journal_entry_and_posted_ledger(self):
        setup = self.create_entity_setup(name="API TX Posted Filter Entity")
        posted_transaction = self.create_transaction_for_entity(
            setup,
            ledger_xid="api-tx-posted-both",
            posted_ledger=True,
            posted_journal_entry=True,
            description="API TX Posted Both",
        )
        journal_entry_only_posted = self.create_transaction_for_entity(
            setup,
            ledger_xid="api-tx-posted-je-only",
            posted_ledger=False,
            posted_journal_entry=True,
            description="API TX Posted Journal Entry Only",
        )
        ledger_only_posted = self.create_transaction_for_entity(
            setup,
            ledger_xid="api-tx-posted-ledger-only",
            posted_ledger=True,
            posted_journal_entry=False,
            description="API TX Posted Ledger Only",
        )

        posted_qs = TransactionModel.objects.for_entity(setup["entity_model"]).posted()

        self.assertTrue(posted_qs.filter(uuid=posted_transaction.uuid).exists())
        self.assertFalse(posted_qs.filter(uuid=journal_entry_only_posted.uuid).exists())
        self.assertFalse(posted_qs.filter(uuid=ledger_only_posted.uuid).exists())
