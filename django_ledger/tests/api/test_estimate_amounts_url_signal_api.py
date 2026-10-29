"""
Smoke tests for EstimateModel amount, URL, display, and signal behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_INVENTORY,
    COGS,
    INCOME_OPERATIONAL,
)
from django_ledger.models import EstimateModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.signals import (
    estimate_status_approved,
    estimate_status_canceled,
    estimate_status_completed,
    estimate_status_draft,
    estimate_status_in_review,
    estimate_status_void,
)


class EstimateAmountsURLSignalAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_estimate_amount_url_signal_user",
            email="api-estimate-amount-url-signal-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Estimate Amount URL Signal Entity"):
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
            code="1410",
            name=f"{name} Inventory Account",
            role=ASSET_CA_INVENTORY,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="5010",
            name=f"{name} COGS Account",
            role=COGS,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="4010",
            name=f"{name} Income Account",
            role=INCOME_OPERATIONAL,
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f"Unit {str(entity_model.uuid)[:8]}",
            unit_abbr=f"e-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )
        customer_model = CustomerModel(
            customer_name=f"{name} Customer",
            entity_model=entity_model,
            description=f"{name} customer.",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "customer_model": customer_model,
            "service_item": service_item,
        }

    def create_estimate(self, setup, *, title="API Estimate Amount URL Signal Contract"):
        estimate_model = setup["entity_model"].create_estimate(
            estimate_title=title,
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=setup["customer_model"],
            date_draft=date(2025, 1, 15),
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def migrate_service_item(self, estimate_model, setup, *, quantity="1.00", unit_cost="100.00", unit_revenue="150.00"):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        unit_revenue = Decimal(unit_revenue)
        estimate_model.migrate_itemtxs(
            itemtxs={
                setup["service_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "unit_revenue": unit_revenue,
                    "total_amount": quantity * unit_revenue,
                }
            },
            operation=EstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def make_review_estimate(self, setup):
        estimate_model = self.migrate_service_item(self.create_estimate(setup), setup)
        estimate_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        estimate_model.refresh_from_db()
        return estimate_model

    def make_approved_estimate(self, setup):
        estimate_model = self.make_review_estimate(setup)
        estimate_model.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))
        estimate_model.refresh_from_db()
        return estimate_model

    def collect_signal_calls(self, signal):
        calls = []
        dispatch_uid = f"{self.id()}-{id(signal)}"

        def receiver(sender, **kwargs):
            calls.append(kwargs)

        signal.connect(
            receiver,
            sender=EstimateModel,
            weak=False,
            dispatch_uid=dispatch_uid,
        )
        self.addCleanup(
            signal.disconnect,
            sender=EstimateModel,
            dispatch_uid=dispatch_uid,
        )
        return calls

    def assert_signal_received_once(self, calls, estimate_model, *, commit):
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["instance"], estimate_model)
        self.assertEqual(calls[0]["commited"], commit)

    def assert_entity_estimate_url(self, url, setup, estimate_model):
        self.assertIsInstance(url, str)
        self.assertIn(setup["entity_model"].slug, url)
        self.assertIn(str(estimate_model.uuid), url)

    def test_amount_helpers_calculate_cost_revenue_profit_and_markup_style_margin(self):
        setup = self.create_entity_setup(name="API Estimate Amount Helper Entity")
        estimate_model = self.migrate_service_item(self.create_estimate(setup), setup)

        self.assertEqual(estimate_model.get_cost_estimate(), Decimal("100.00"))
        self.assertEqual(estimate_model.get_revenue_estimate(), Decimal("150.00"))
        self.assertEqual(estimate_model.get_profit_estimate(), Decimal("50.00"))
        self.assertEqual(estimate_model.get_cost_estimate(as_float=True), 100.0)
        self.assertEqual(estimate_model.get_revenue_estimate(as_float=True), 150.0)
        self.assertEqual(estimate_model.get_profit_estimate(as_float=True), 50.0)
        self.assertAlmostEqual(estimate_model.get_gross_margin_estimate(), 0.5)
        self.assertAlmostEqual(estimate_model.get_gross_margin_estimate(as_percent=True), 50.0)

    def test_update_cost_and_revenue_estimate_use_item_transaction_totals(self):
        setup = self.create_entity_setup(name="API Estimate Amount Update Entity")
        estimate_model = self.migrate_service_item(self.create_estimate(setup), setup)
        itemtxs_qs, _itemtxs_data = estimate_model.get_itemtxs_data()

        estimate_model.revenue_estimate = Decimal("0.00")
        estimate_model.labor_estimate = Decimal("0.00")
        estimate_model.update_revenue_estimate(itemtxs_qs=itemtxs_qs)
        estimate_model.update_cost_estimate(itemtxs_qs=itemtxs_qs)

        self.assertEqual(estimate_model.revenue_estimate, Decimal("150.00"))
        self.assertEqual(estimate_model.labor_estimate, Decimal("100.00"))

    def test_contract_summary_returns_estimate_amounts_and_zero_downstream_aggregates(self):
        setup = self.create_entity_setup(name="API Estimate Contract Summary Entity")
        estimate_model = self.make_approved_estimate(setup)

        summary = estimate_model.get_contract_summary()

        self.assertEqual(summary["cost_estimate"], 100.0)
        self.assertEqual(summary["revenue_estimate"], 150.0)
        self.assertEqual(float(summary["po_amount__sum"]), 0.0)
        self.assertEqual(float(summary["bill_amount_due__sum"]), 0.0)
        self.assertEqual(float(summary["invoice_amount_due__sum"]), 0.0)

    def test_url_helpers_return_entity_scoped_strings(self):
        setup = self.create_entity_setup(name="API Estimate URL Helper Entity")
        estimate_model = self.create_estimate(setup)

        url_helpers = [
            estimate_model.get_mark_as_draft_url,
            estimate_model.get_mark_as_review_url,
            estimate_model.get_mark_as_approved_url,
            estimate_model.get_mark_as_completed_url,
            estimate_model.get_mark_as_canceled_url,
            estimate_model.get_mark_as_void_url,
        ]

        for helper in url_helpers:
            self.assert_entity_estimate_url(helper(), setup, estimate_model)

    def test_display_message_and_html_helpers_include_stable_context(self):
        setup = self.create_entity_setup(name="API Estimate Display Helper Entity")
        estimate_model = self.create_estimate(setup)

        self.assertIn(estimate_model.estimate_number, str(estimate_model))
        self.assertIn(estimate_model.title, str(estimate_model))
        self.assertTrue(str(estimate_model).startswith("Estimate "))

        approved_estimate = self.make_approved_estimate(setup)
        self.assertTrue(str(approved_estimate).startswith("Contract "))

        html_helpers = [
            estimate_model.get_html_id,
            estimate_model.get_mark_as_draft_html_id,
            estimate_model.get_mark_as_review_html_id,
            estimate_model.get_mark_as_approved_html_id,
            estimate_model.get_mark_as_completed_html_id,
            estimate_model.get_mark_as_canceled_html_id,
            estimate_model.get_mark_as_void_html_id,
        ]
        for helper in html_helpers:
            self.assertIn(str(estimate_model.uuid), helper())

        message_helpers = [
            estimate_model.get_mark_as_draft_message,
            estimate_model.get_mark_as_review_message,
            estimate_model.get_mark_as_approved_message,
            estimate_model.get_mark_as_completed_message,
            estimate_model.get_mark_as_canceled_message,
            estimate_model.get_mark_as_void_message,
        ]
        for helper in message_helpers:
            self.assertIn(estimate_model.estimate_number, helper())

    def test_mark_as_review_emits_estimate_status_in_review_signal(self):
        setup = self.create_entity_setup(name="API Estimate Review Signal Entity")
        estimate_model = self.migrate_service_item(self.create_estimate(setup), setup)
        calls = self.collect_signal_calls(estimate_status_in_review)

        estimate_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

        self.assert_signal_received_once(calls, estimate_model, commit=True)

    def test_mark_as_draft_emits_estimate_status_draft_signal(self):
        setup = self.create_entity_setup(name="API Estimate Draft Signal Entity")
        estimate_model = self.make_review_estimate(setup)
        calls = self.collect_signal_calls(estimate_status_draft)

        estimate_model.mark_as_draft(commit=True)

        self.assert_signal_received_once(calls, estimate_model, commit=True)

    def test_mark_as_approved_emits_estimate_status_approved_signal(self):
        setup = self.create_entity_setup(name="API Estimate Approved Signal Entity")
        estimate_model = self.make_review_estimate(setup)
        calls = self.collect_signal_calls(estimate_status_approved)

        estimate_model.mark_as_approved(commit=True, date_approved=date(2025, 1, 17))

        self.assert_signal_received_once(calls, estimate_model, commit=True)

    def test_mark_as_completed_emits_estimate_status_completed_signal(self):
        setup = self.create_entity_setup(name="API Estimate Completed Signal Entity")
        estimate_model = self.make_approved_estimate(setup)
        calls = self.collect_signal_calls(estimate_status_completed)

        estimate_model.mark_as_completed(commit=True, date_completed=date(2025, 1, 18))

        self.assert_signal_received_once(calls, estimate_model, commit=True)

    def test_mark_as_canceled_emits_estimate_status_canceled_signal(self):
        setup = self.create_entity_setup(name="API Estimate Canceled Signal Entity")
        estimate_model = self.create_estimate(setup)
        calls = self.collect_signal_calls(estimate_status_canceled)

        estimate_model.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))

        self.assert_signal_received_once(calls, estimate_model, commit=True)

    def test_mark_as_void_emits_estimate_status_void_signal(self):
        setup = self.create_entity_setup(name="API Estimate Void Signal Entity")
        estimate_model = self.make_approved_estimate(setup)
        calls = self.collect_signal_calls(estimate_status_void)

        estimate_model.mark_as_void(commit=True, date_void=date(2025, 1, 19))

        self.assert_signal_received_once(calls, estimate_model, commit=True)
