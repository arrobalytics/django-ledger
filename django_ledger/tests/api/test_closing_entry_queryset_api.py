"""
High-level API tests for ClosingEntryModel queryset and manager behavior.
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


class ClosingEntryQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_closing_entry_queryset_admin",
            email="api-closing-entry-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_closing_entry_queryset_manager",
            email="api-closing-entry-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_closing_entry_queryset_other_admin",
            email="api-closing-entry-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_closing_entry_queryset_unrelated",
            email="api-closing-entry-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_closing_entry_queryset_superuser",
            email="api-closing-entry-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Closing Entry Queryset Entity", admin_user=None, manager_user=None):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=admin_user or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        if manager_user is not None:
            entity_model.managers.add(manager_user)

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

    def create_closing_entry(self, setup, *, closing_date=date(2025, 12, 31), posted=False):
        closing_entry = ClosingEntryModel.objects.create(
            entity_model=setup["entity_model"],
            closing_date=closing_date,
            posted=posted,
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

    def assert_closing_entry_uuids(self, queryset, expected_entries):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {closing_entry.uuid for closing_entry in expected_entries},
        )

    def assert_closing_tx_uuids(self, queryset, expected_txs):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {closing_tx.uuid for closing_tx in expected_txs},
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API Closing Entry Queryset Entity A")
        other_setup = self.create_entity_setup(
            name="API Closing Entry Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        closing_entry = self.create_closing_entry(setup)
        self.create_closing_entry(other_setup)
        entity_model = setup["entity_model"]

        self.assert_closing_entry_uuids(ClosingEntryModel.objects.for_entity(entity_model), [closing_entry])
        self.assert_closing_entry_uuids(ClosingEntryModel.objects.for_entity(entity_model.slug), [closing_entry])
        self.assert_closing_entry_uuids(ClosingEntryModel.objects.for_entity(entity_model.uuid), [closing_entry])

    def test_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_closing_entry(self.create_entity_setup())

        with self.assertRaises(ClosingEntryValidationError):
            ClosingEntryModel.objects.for_entity(object())

        self.assertFalse(ClosingEntryModel.objects.for_entity("missing-closing-entry-entity").exists())

    def test_for_user_scopes_to_authorized_users_and_superuser(self):
        setup = self.create_entity_setup(
            name="API Closing Entry Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_setup = self.create_entity_setup(
            name="API Closing Entry Queryset Other Access Entity",
            admin_user=self.other_admin_user,
        )
        closing_entry = self.create_closing_entry(setup)
        other_closing_entry = self.create_closing_entry(other_setup)

        self.assert_closing_entry_uuids(ClosingEntryModel.objects.all().for_user(self.admin_user), [closing_entry])
        self.assert_closing_entry_uuids(ClosingEntryModel.objects.all().for_user(self.manager_user), [closing_entry])
        self.assertFalse(ClosingEntryModel.objects.all().for_user(self.unrelated_user).exists())
        self.assert_closing_entry_uuids(
            ClosingEntryModel.objects.all().for_user(self.superuser),
            [closing_entry, other_closing_entry],
        )

    def test_posted_and_not_posted_filters_return_matching_entries(self):
        setup = self.create_entity_setup(name="API Closing Entry Queryset Posted Entity")
        posted_entry = self.create_closing_entry(setup, closing_date=date(2025, 12, 31), posted=True)
        unposted_entry = self.create_closing_entry(setup, closing_date=date(2025, 11, 30), posted=False)

        scoped_qs = ClosingEntryModel.objects.for_entity(setup["entity_model"])

        self.assert_closing_entry_uuids(scoped_qs.posted(), [posted_entry])
        self.assert_closing_entry_uuids(scoped_qs.not_posted(), [unposted_entry])

    def test_manager_annotation_exposes_closing_transaction_count(self):
        setup = self.create_entity_setup(name="API Closing Entry Queryset Count Entity")
        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_transactions(closing_entry, setup)

        annotated_entry = ClosingEntryModel.objects.get(uuid=closing_entry.uuid)

        self.assertEqual(annotated_entry.ce_txs_count, 2)

    def test_closing_transaction_for_user_scopes_to_authorized_users(self):
        setup = self.create_entity_setup(
            name="API Closing Tx Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_setup = self.create_entity_setup(
            name="API Closing Tx Queryset Other Entity",
            admin_user=self.other_admin_user,
        )
        closing_entry = self.create_closing_entry(setup)
        other_closing_entry = self.create_closing_entry(other_setup)
        debit_tx, credit_tx = self.create_balanced_closing_transactions(closing_entry, setup)
        other_debit_tx, other_credit_tx = self.create_balanced_closing_transactions(other_closing_entry, other_setup)

        self.assert_closing_tx_uuids(
            ClosingEntryTransactionModel.objects.all().for_user(self.admin_user),
            [debit_tx, credit_tx],
        )
        self.assert_closing_tx_uuids(
            ClosingEntryTransactionModel.objects.all().for_user(self.manager_user),
            [debit_tx, credit_tx],
        )
        self.assertFalse(ClosingEntryTransactionModel.objects.all().for_user(self.unrelated_user).exists())
        self.assert_closing_tx_uuids(
            ClosingEntryTransactionModel.objects.all().for_user(self.superuser),
            [debit_tx, credit_tx, other_debit_tx, other_credit_tx],
        )

    def test_closing_transaction_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API Closing Tx Queryset Entity A")
        other_setup = self.create_entity_setup(
            name="API Closing Tx Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        closing_entry = self.create_closing_entry(setup)
        other_closing_entry = self.create_closing_entry(other_setup)
        debit_tx, credit_tx = self.create_balanced_closing_transactions(closing_entry, setup)
        self.create_balanced_closing_transactions(other_closing_entry, other_setup)
        entity_model = setup["entity_model"]

        self.assert_closing_tx_uuids(
            ClosingEntryTransactionModel.objects.for_entity(entity_model),
            [debit_tx, credit_tx],
        )
        self.assert_closing_tx_uuids(
            ClosingEntryTransactionModel.objects.for_entity(entity_model.slug),
            [debit_tx, credit_tx],
        )
        self.assert_closing_tx_uuids(
            ClosingEntryTransactionModel.objects.for_entity(entity_model.uuid),
            [debit_tx, credit_tx],
        )

    def test_closing_transaction_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        setup = self.create_entity_setup(name="API Closing Tx Queryset Invalid Entity")
        closing_entry = self.create_closing_entry(setup)
        self.create_balanced_closing_transactions(closing_entry, setup)

        with self.assertRaises(ClosingEntryValidationError):
            ClosingEntryTransactionModel.objects.for_entity(object())

        self.assertFalse(ClosingEntryTransactionModel.objects.for_entity("missing-closing-tx-entity").exists())
