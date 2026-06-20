"""
High-level API behavior tests for StagedTransactionModel split helpers.

These tests cover split state and commit-dictionary behavior without exercising
migration, matching, receipts, undo, or URL helpers.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, CREDIT, DEBIT
from django_ledger.models import BankAccountModel
from django_ledger.models.data_import import (
    ImportJobModel,
    StagedTransactionModel,
)
from django_ledger.models.entity import EntityModel


class StagedTransactionSplitCommitAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_staged_transaction_split_admin",
            email="api-staged-transaction-split-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(
        self,
        *,
        name="API Staged Transaction Split Entity",
    ):
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
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role="ex_regular",
            balance_type=DEBIT,
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
            user_model=self.admin_user,
            commit=True,
        )
        bank_account.refresh_from_db()
        import_job = ImportJobModel.objects.create(
            description=f"{name} Import Job",
            bank_account_model=bank_account,
        )
        import_job.configure(commit=True)
        import_job.refresh_from_db()
        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "income_account": income_account,
            "expense_account": expense_account,
            "bank_account": bank_account,
            "import_job": import_job,
        }

    def create_staged_transaction(
        self,
        import_job,
        *,
        fit_id="FIT-SPLIT",
        amount="100.00",
        account_model=None,
        parent=None,
        amount_split=None,
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
        )

    def get_annotated_staged_transaction(self, staged_tx):
        return StagedTransactionModel.objects.get(uuid=staged_tx.uuid)

    def test_add_split_commit_false_returns_unsaved_children(self):
        setup = self.create_entity_setup(name="API Staged Split Commit False Entity")
        parent_tx = self.create_staged_transaction(setup["import_job"])
        parent_tx = self.get_annotated_staged_transaction(parent_tx)

        children = parent_tx.add_split(n=1, commit=False)

        self.assertEqual(len(children), 2)
        for child in children:
            self.assertTrue(child._state.adding)
            self.assertEqual(child.parent, parent_tx)
            self.assertEqual(child.import_job_id, setup["import_job"].uuid)
            self.assertEqual(child.fit_id, parent_tx.fit_id)
            self.assertEqual(child.amount_split, Decimal("0.00"))

        parent_tx = self.get_annotated_staged_transaction(parent_tx)
        self.assertFalse(parent_tx.has_children())
        self.assertFalse(
            StagedTransactionModel.objects.filter(parent=parent_tx).exists()
        )

    def test_add_split_commit_true_creates_children(self):
        setup = self.create_entity_setup(name="API Staged Split Commit True Entity")
        parent_tx = self.create_staged_transaction(setup["import_job"])
        parent_tx = self.get_annotated_staged_transaction(parent_tx)

        children = parent_tx.add_split(n=1, commit=True)
        parent_tx = self.get_annotated_staged_transaction(parent_tx)
        child_qs = StagedTransactionModel.objects.filter(parent=parent_tx)

        self.assertEqual(len(children), 2)
        self.assertEqual(child_qs.count(), 2)
        self.assertTrue(parent_tx.has_children())
        self.assertTrue(parent_tx.is_bundled())
        for child in child_qs:
            self.assertTrue(child.is_children())
            self.assertEqual(child.parent_id, parent_tx.uuid)
            self.assertEqual(child.import_job_id, setup["import_job"].uuid)

    def test_add_split_on_already_split_parent_appends_one_child(self):
        setup = self.create_entity_setup(name="API Staged Split Guard Entity")
        parent_tx = self.create_staged_transaction(setup["import_job"])
        parent_tx = self.get_annotated_staged_transaction(parent_tx)
        parent_tx.add_split(n=1, commit=True)
        parent_tx = self.get_annotated_staged_transaction(parent_tx)
        children_count = StagedTransactionModel.objects.filter(parent=parent_tx).count()

        additional_children = parent_tx.add_split(commit=True)
        parent_tx = self.get_annotated_staged_transaction(parent_tx)

        self.assertEqual(len(additional_children), 1)
        self.assertEqual(
            children_count + 1,
            StagedTransactionModel.objects.filter(parent=parent_tx).count(),
        )

    def test_split_amount_totals_and_mapping_state_helpers(self):
        setup = self.create_entity_setup(name="API Staged Split Totals Entity")
        parent_tx = self.create_staged_transaction(setup["import_job"], amount="100.00")
        parent_tx = self.get_annotated_staged_transaction(parent_tx)
        parent_tx.add_split(n=1, commit=True)
        children = list(StagedTransactionModel.objects.filter(parent=parent_tx))
        children[0].amount_split = Decimal("60.00")
        children[0].account_model = setup["income_account"]
        children[0].save(update_fields=["amount_split", "account_model", "updated"])
        children[1].amount_split = Decimal("40.00")
        children[1].account_model = setup["expense_account"]
        children[1].save(update_fields=["amount_split", "account_model", "updated"])

        parent_tx = self.get_annotated_staged_transaction(parent_tx)

        self.assertTrue(parent_tx.is_total_amount_split())
        self.assertTrue(parent_tx.are_all_children_mapped())

        children[1].amount_split = Decimal("39.00")
        children[1].account_model = None
        children[1].save(update_fields=["amount_split", "account_model", "updated"])
        parent_tx = self.get_annotated_staged_transaction(parent_tx)

        self.assertFalse(parent_tx.is_total_amount_split())
        self.assertFalse(parent_tx.are_all_children_mapped())

    def test_commit_dict_for_positive_and_negative_amounts_uses_expected_debit_credit_sides(self):
        setup = self.create_entity_setup(name="API Staged Commit Direction Entity")
        positive_tx = self.create_staged_transaction(
            setup["import_job"],
            fit_id="FIT-POSITIVE",
            amount="125.00",
            account_model=setup["income_account"],
        )
        negative_tx = self.create_staged_transaction(
            setup["import_job"],
            fit_id="FIT-NEGATIVE",
            amount="-75.00",
            account_model=setup["expense_account"],
        )
        positive_tx = self.get_annotated_staged_transaction(positive_tx)
        negative_tx = self.get_annotated_staged_transaction(negative_tx)

        positive_commit = positive_tx.commit_dict()[0]
        negative_commit = negative_tx.commit_dict()[0]

        self.assertEqual(positive_commit[0]["account"], setup["cash_account"])
        self.assertEqual(positive_commit[0]["amount"], Decimal("125.00"))
        self.assertEqual(positive_commit[0]["tx_type"], DEBIT)
        self.assertEqual(positive_commit[1]["account"], setup["income_account"])
        self.assertEqual(positive_commit[1]["amount"], Decimal("125.00"))
        self.assertEqual(positive_commit[1]["amount_staged"], Decimal("125.00"))
        self.assertEqual(positive_commit[1]["tx_type"], CREDIT)

        self.assertEqual(negative_commit[0]["account"], setup["cash_account"])
        self.assertEqual(negative_commit[0]["amount"], Decimal("75.00"))
        self.assertEqual(negative_commit[0]["tx_type"], CREDIT)
        self.assertEqual(negative_commit[1]["account"], setup["expense_account"])
        self.assertEqual(negative_commit[1]["amount"], Decimal("75.00"))
        self.assertEqual(negative_commit[1]["amount_staged"], Decimal("-75.00"))
        self.assertEqual(negative_commit[1]["tx_type"], DEBIT)

    def test_commit_dict_split_txs_uses_child_amounts_and_accounts(self):
        setup = self.create_entity_setup(name="API Staged Split Commit Dict Entity")
        parent_tx = self.create_staged_transaction(setup["import_job"], amount="100.00")
        parent_tx = self.get_annotated_staged_transaction(parent_tx)
        parent_tx.add_split(n=1, commit=True)
        children = list(StagedTransactionModel.objects.filter(parent=parent_tx).order_by("uuid"))
        children[0].amount_split = Decimal("60.00")
        children[0].account_model = setup["income_account"]
        children[0].save(update_fields=["amount_split", "account_model", "updated"])
        children[1].amount_split = Decimal("40.00")
        children[1].account_model = setup["expense_account"]
        children[1].save(update_fields=["amount_split", "account_model", "updated"])
        parent_tx = self.get_annotated_staged_transaction(parent_tx)

        split_commit = parent_tx.commit_dict(split_txs=True)

        self.assertEqual(len(split_commit), 2)

        child_entries_by_account = {
            entry[1]["account"].uuid: entry
            for entry in split_commit
        }

        income_entry = child_entries_by_account[setup["income_account"].uuid]
        expense_entry = child_entries_by_account[setup["expense_account"].uuid]

        self.assertEqual(income_entry[0]["account"], setup["cash_account"])
        self.assertEqual(income_entry[0]["amount"], Decimal("60.00"))
        self.assertEqual(income_entry[0]["tx_type"], DEBIT)
        self.assertEqual(income_entry[1]["amount"], Decimal("60.00"))
        self.assertEqual(income_entry[1]["amount_staged"], Decimal("60.00"))
        self.assertEqual(income_entry[1]["tx_type"], CREDIT)

        self.assertEqual(expense_entry[0]["account"], setup["cash_account"])
        self.assertEqual(expense_entry[0]["amount"], Decimal("40.00"))
        self.assertEqual(expense_entry[0]["tx_type"], DEBIT)
        self.assertEqual(expense_entry[1]["amount"], Decimal("40.00"))
        self.assertEqual(expense_entry[1]["amount_staged"], Decimal("40.00"))
        self.assertEqual(expense_entry[1]["tx_type"], CREDIT)
