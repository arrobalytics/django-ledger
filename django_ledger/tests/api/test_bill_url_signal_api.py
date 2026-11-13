"""
Smoke tests for BillModel URL, display, and lifecycle signal behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_PREPAID,
    EXPENSE_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
)
from django_ledger.models import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.signals import (
    bill_status_approved,
    bill_status_canceled,
    bill_status_draft,
    bill_status_in_review,
    bill_status_paid,
    bill_status_void,
)


class BillURLSignalAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_bill_url_signal_user",
            email="api-bill-url-signal-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Bill URL Signal Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        coa_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role=ASSET_CA_CASH,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="1310",
            name=f"{name} Prepaid Account",
            role=ASSET_CA_PREPAID,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="2010",
            name=f"{name} Accounts Payable",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role=EXPENSE_OPERATIONAL,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f"{name} Unit",
            unit_abbr=f"b-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )
        vendor_model = entity_model.create_vendor(
            {
                "vendor_name": f"{name} Vendor",
                "description": f"{name} vendor.",
                "active": True,
                "hidden": False,
            },
            commit=True,
        )
        expense_item = entity_model.create_item_expense(
            name=f"{name} Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "vendor_model": vendor_model,
            "expense_item": expense_item,
        }

    def create_bill(self, setup):
        bill_model = setup["entity_model"].create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_NET_30,
            date_draft=date(2025, 1, 15),
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def migrate_expense_item(self, bill_model, setup):
        bill_model.migrate_itemtxs(
            itemtxs={
                setup["expense_item"].item_number: {
                    "quantity": Decimal("1.00"),
                    "unit_cost": Decimal("100.00"),
                    "total_amount": Decimal("100.00"),
                }
            },
            operation=BillModel.ITEMIZE_REPLACE,
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def make_review_bill(self, setup):
        bill_model = self.migrate_expense_item(self.create_bill(setup), setup)
        bill_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        bill_model.refresh_from_db()
        return bill_model

    def make_approved_bill(self, setup):
        bill_model = self.make_review_bill(setup)
        bill_model.mark_as_approved(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_approved=date(2025, 1, 17),
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def collect_signal_calls(self, signal):
        calls = []
        dispatch_uid = f"{self.id()}-{id(signal)}"

        def receiver(sender, **kwargs):
            calls.append(kwargs)

        signal.connect(
            receiver,
            sender=BillModel,
            weak=False,
            dispatch_uid=dispatch_uid,
        )
        self.addCleanup(
            signal.disconnect,
            sender=BillModel,
            dispatch_uid=dispatch_uid,
        )
        return calls

    def assert_signal_received_once(self, calls, bill_model, *, commit):
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["instance"], bill_model)
        self.assertEqual(calls[0]["commited"], commit)

    def assert_entity_bill_url(self, url, setup, bill_model):
        self.assertIsInstance(url, str)
        self.assertIn(setup["entity_model"].slug, url)
        self.assertIn(str(bill_model.uuid), url)

    def test_url_helpers_return_entity_scoped_strings(self):
        setup = self.create_entity_setup(name="API Bill URL Helper Entity")
        bill_model = self.create_bill(setup)

        url_helpers = [
            bill_model.get_absolute_url,
            bill_model.get_mark_as_draft_url,
            bill_model.get_mark_as_review_url,
            bill_model.get_mark_as_approved_url,
            bill_model.get_mark_as_paid_url,
            bill_model.get_mark_as_void_url,
            bill_model.get_mark_as_canceled_url,
        ]

        for helper in url_helpers:
            self.assert_entity_bill_url(helper(), setup, bill_model)

    def test_display_message_and_html_helpers_include_stable_context(self):
        setup = self.create_entity_setup(name="API Bill Display Helper Entity")
        bill_model = self.create_bill(setup)

        self.assertIn(bill_model.bill_number, str(bill_model))
        self.assertIn(bill_model.get_bill_status_display(), str(bill_model))

        title = bill_model.generate_descriptive_title()
        self.assertIn(bill_model.bill_number, title)
        self.assertIn(setup["vendor_model"].vendor_name, title)
        self.assertIn(bill_model.get_bill_status_display(), title)

        html_helpers = [
            bill_model.get_html_id,
            bill_model.get_html_amount_due_id,
            bill_model.get_html_amount_paid_id,
            bill_model.get_html_form_id,
            bill_model.get_mark_as_draft_html_id,
            bill_model.get_mark_as_review_html_id,
            bill_model.get_mark_as_approved_html_id,
            bill_model.get_mark_as_paid_html_id,
            bill_model.get_mark_as_void_html_id,
            bill_model.get_mark_as_canceled_html_id,
        ]
        for helper in html_helpers:
            self.assertIn(str(bill_model.uuid), helper())

        message_helpers = [
            bill_model.get_mark_as_draft_message,
            bill_model.get_mark_as_review_message,
            bill_model.get_mark_as_approved_message,
            bill_model.get_mark_as_paid_message,
            bill_model.get_mark_as_void_message,
            bill_model.get_mark_as_canceled_message,
        ]
        for helper in message_helpers:
            self.assertIn(bill_model.bill_number, helper())

    def test_mark_as_review_emits_bill_status_in_review_signal(self):
        setup = self.create_entity_setup(name="API Bill Review Signal Entity")
        bill_model = self.migrate_expense_item(self.create_bill(setup), setup)
        calls = self.collect_signal_calls(bill_status_in_review)

        bill_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

        self.assert_signal_received_once(calls, bill_model, commit=True)

    def test_mark_as_draft_emits_bill_status_draft_signal(self):
        setup = self.create_entity_setup(name="API Bill Draft Signal Entity")
        bill_model = self.make_review_bill(setup)
        calls = self.collect_signal_calls(bill_status_draft)

        bill_model.mark_as_draft(commit=True, date_draft=date(2025, 1, 17))

        self.assert_signal_received_once(calls, bill_model, commit=True)

    def test_mark_as_approved_emits_bill_status_approved_signal(self):
        setup = self.create_entity_setup(name="API Bill Approved Signal Entity")
        bill_model = self.make_review_bill(setup)
        calls = self.collect_signal_calls(bill_status_approved)

        bill_model.mark_as_approved(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_approved=date(2025, 1, 17),
            commit=True,
        )

        self.assert_signal_received_once(calls, bill_model, commit=True)

    def test_mark_as_paid_emits_bill_status_paid_signal(self):
        setup = self.create_entity_setup(name="API Bill Paid Signal Entity")
        bill_model = self.make_approved_bill(setup)
        calls = self.collect_signal_calls(bill_status_paid)

        bill_model.mark_as_paid(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_paid=date(2025, 1, 18),
            commit=True,
        )

        self.assert_signal_received_once(calls, bill_model, commit=True)

    def test_mark_as_canceled_emits_bill_status_canceled_signal(self):
        setup = self.create_entity_setup(name="API Bill Canceled Signal Entity")
        bill_model = self.create_bill(setup)
        calls = self.collect_signal_calls(bill_status_canceled)

        bill_model.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))

        self.assert_signal_received_once(calls, bill_model, commit=True)

    def test_mark_as_void_emits_bill_status_void_signal(self):
        setup = self.create_entity_setup(name="API Bill Void Signal Entity")
        bill_model = self.make_approved_bill(setup)
        calls = self.collect_signal_calls(bill_status_void)

        bill_model.mark_as_void(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_void=date(2025, 1, 19),
            commit=True,
        )

        self.assert_signal_received_once(calls, bill_model, commit=True)
