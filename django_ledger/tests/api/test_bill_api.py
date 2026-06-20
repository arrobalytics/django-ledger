"""
High-level API behavior tests for BillModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import BillModel, ItemTransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.vendor import VendorModel


class BillHighLevelAPITest(TestCase):
    """
    High-level behavior tests for BillModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic bill/vendor/item lifecycle invariants
    that should remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_bill_contract_user",
            email="api-bill-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_with_bill_setup(self, *, name="API Bill Contract Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Bill Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        cash_account = coa_model.create_account(
            code="1010",
            name="API Bill Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        prepaid_account = coa_model.create_account(
            code="1310",
            name="API Bill Prepaid Account",
            role="asset_ca_prepaid",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        unearned_account = coa_model.create_account(
            code="2010",
            name="API Bill Accounts Payable",
            role="lia_cl_acc_payable",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        expense_account = coa_model.create_account(
            code="6010",
            name="API Bill Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        uom_model = entity_model.create_uom(
            name="API Bill Unit",
            unit_abbr="api-bill",
            active=True,
            commit=True,
        )

        vendor_model = VendorModel(
            vendor_name="API Bill Vendor",
            entity_model=entity_model,
            description="API Bill Vendor description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()

        expense_item = entity_model.create_item_expense(
            name="API Bill Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "prepaid_account": prepaid_account,
            "unearned_account": unearned_account,
            "expense_account": expense_account,
            "uom_model": uom_model,
            "vendor_model": vendor_model,
            "expense_item": expense_item,
        }

    def create_configured_bill(self, setup):
        bill_model = BillModel(
            vendor=setup["vendor_model"],
            cash_account=setup["cash_account"],
            prepaid_account=setup["prepaid_account"],
            unearned_account=setup["unearned_account"],
        )

        _ledger_model, bill_model = bill_model.configure(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            date_draft=date(2026, 1, 15),
            commit=True,
        )

        return bill_model

    def migrate_expense_item(self, bill_model, setup, *, quantity="2.00", unit_cost="50.00"):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)

        itemtxs = {
            setup["expense_item"].item_number: {
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_amount": quantity * unit_cost,
            }
        }

        bill_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=BillModel.ITEMIZE_REPLACE,
            commit=True,
        )

        bill_model.refresh_from_db()
        return bill_model

    def test_bill_configure_creates_draft_bill_under_entity_and_vendor(self):
        setup = self.create_entity_with_bill_setup()

        bill_model = self.create_configured_bill(setup)

        self.assertIsInstance(bill_model, BillModel)
        self.assertIsNotNone(bill_model.uuid)
        self.assertEqual(bill_model.entity_model_id, setup["entity_model"].uuid)
        self.assertEqual(bill_model.vendor_id, setup["vendor_model"].uuid)
        self.assertTrue(bill_model.is_draft())
        self.assertFalse(bill_model.is_approved())
        self.assertFalse(bill_model.is_paid())
        self.assertTrue(bill_model.bill_number)

    def test_bill_item_migration_creates_item_transaction(self):
        setup = self.create_entity_with_bill_setup()
        bill_model = self.create_configured_bill(setup)

        self.migrate_expense_item(bill_model, setup)

        item_txs = ItemTransactionModel.objects.filter(bill_model=bill_model)

        self.assertEqual(item_txs.count(), 1)

        item_tx = item_txs.get()

        self.assertEqual(item_tx.item_model_id, setup["expense_item"].uuid)
        self.assertEqual(item_tx.quantity, Decimal("2.00"))
        self.assertEqual(item_tx.unit_cost, Decimal("50.00"))
        self.assertEqual(item_tx.total_amount, Decimal("100.00"))

    def test_bill_item_migration_updates_amount_due(self):
        setup = self.create_entity_with_bill_setup()
        bill_model = self.create_configured_bill(setup)

        bill_model = self.migrate_expense_item(bill_model, setup)

        self.assertEqual(bill_model.amount_due, Decimal("100.00"))
        self.assertEqual(bill_model.amount_paid, Decimal("0.00"))

    def test_bill_for_entity_queryset_limits_scope(self):
        setup = self.create_entity_with_bill_setup(name="API Bill Entity A")
        other_setup = self.create_entity_with_bill_setup(name="API Bill Entity B")

        bill_model = self.create_configured_bill(setup)
        other_bill_model = self.create_configured_bill(other_setup)

        scoped_qs = BillModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(scoped_qs.filter(uuid=bill_model.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_bill_model.uuid).exists())

    def test_bill_can_move_from_draft_to_review(self):
        setup = self.create_entity_with_bill_setup()
        bill_model = self.create_configured_bill(setup)
        bill_model = self.migrate_expense_item(bill_model, setup)

        bill_model.mark_as_review(commit=True)
        bill_model.refresh_from_db()

        self.assertTrue(bill_model.is_review())
        self.assertFalse(bill_model.is_draft())

    def test_bill_can_move_from_review_to_approved(self):
        setup = self.create_entity_with_bill_setup()
        bill_model = self.create_configured_bill(setup)
        bill_model = self.migrate_expense_item(bill_model, setup)

        bill_model.mark_as_review(commit=True)
        bill_model.refresh_from_db()

        bill_model.mark_as_approved(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        bill_model.refresh_from_db()

        self.assertTrue(bill_model.is_approved())
        self.assertFalse(bill_model.is_paid())
        self.assertEqual(bill_model.amount_due, Decimal("100.00"))

    def test_approved_bill_can_be_marked_paid(self):
        setup = self.create_entity_with_bill_setup()
        bill_model = self.create_configured_bill(setup)
        bill_model = self.migrate_expense_item(bill_model, setup)

        bill_model.mark_as_review(commit=True)
        bill_model.refresh_from_db()

        bill_model.mark_as_approved(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        bill_model.refresh_from_db()

        bill_model.mark_as_paid(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        bill_model.refresh_from_db()

        self.assertTrue(bill_model.is_paid())
        self.assertEqual(bill_model.amount_paid, bill_model.amount_due)
