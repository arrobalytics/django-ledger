"""
Smoke tests for InvoiceModel URL, display, and lifecycle signal behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_RECEIVABLES,
    COGS,
    INCOME_OPERATIONAL,
    LIABILITY_CL_DEFERRED_REVENUE,
)
from django_ledger.models import InvoiceModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.signals import (
    invoice_status_approved,
    invoice_status_canceled,
    invoice_status_draft,
    invoice_status_in_review,
    invoice_status_paid,
    invoice_status_void,
)


class InvoiceURLSignalAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_invoice_url_signal_user",
            email="api-invoice-url-signal-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Invoice URL Signal Entity"):
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
            code="1210",
            name=f"{name} Receivable Account",
            role=ASSET_CA_RECEIVABLES,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="2310",
            name=f"{name} Deferred Revenue Account",
            role=LIABILITY_CL_DEFERRED_REVENUE,
            balance_type="credit",
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
            name=f"{name} Unit",
            unit_abbr=f"i-{str(entity_model.uuid)[:6]}",
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

    def create_invoice(self, setup):
        invoice_model = setup["entity_model"].create_invoice(
            customer_model=setup["customer_model"],
            terms=InvoiceModel.TERMS_NET_30,
            date_draft=date(2025, 1, 15),
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def migrate_service_item(self, invoice_model, setup):
        invoice_model.migrate_itemtxs(
            itemtxs={
                setup["service_item"].item_number: {
                    "quantity": Decimal("1.00"),
                    "unit_cost": Decimal("100.00"),
                    "total_amount": Decimal("100.00"),
                }
            },
            operation=InvoiceModel.ITEMIZE_REPLACE,
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def make_review_invoice(self, setup):
        invoice_model = self.migrate_service_item(self.create_invoice(setup), setup)
        invoice_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))
        invoice_model.refresh_from_db()
        return invoice_model

    def make_approved_invoice(self, setup):
        invoice_model = self.make_review_invoice(setup)
        invoice_model.mark_as_approved(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_approved=date(2025, 1, 17),
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def collect_signal_calls(self, signal):
        calls = []
        dispatch_uid = f"{self.id()}-{id(signal)}"

        def receiver(sender, **kwargs):
            calls.append(kwargs)

        signal.connect(
            receiver,
            sender=InvoiceModel,
            weak=False,
            dispatch_uid=dispatch_uid,
        )
        self.addCleanup(
            signal.disconnect,
            sender=InvoiceModel,
            dispatch_uid=dispatch_uid,
        )
        return calls

    def assert_signal_received_once(self, calls, invoice_model, *, commit):
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["instance"], invoice_model)
        self.assertEqual(calls[0]["commited"], commit)

    def assert_entity_invoice_url(self, url, setup, invoice_model):
        self.assertIsInstance(url, str)
        self.assertIn(setup["entity_model"].slug, url)
        self.assertIn(str(invoice_model.uuid), url)

    def test_url_helpers_return_entity_scoped_strings(self):
        setup = self.create_entity_setup(name="API Invoice URL Helper Entity")
        invoice_model = self.create_invoice(setup)

        url_helpers = [
            invoice_model.get_absolute_url,
            invoice_model.get_mark_as_draft_url,
            invoice_model.get_mark_as_review_url,
            invoice_model.get_mark_as_approved_url,
            invoice_model.get_mark_as_paid_url,
            invoice_model.get_mark_as_void_url,
            invoice_model.get_mark_as_canceled_url,
        ]

        for helper in url_helpers:
            self.assert_entity_invoice_url(helper(), setup, invoice_model)

    def test_display_message_and_html_helpers_include_stable_context(self):
        setup = self.create_entity_setup(name="API Invoice Display Helper Entity")
        invoice_model = self.create_invoice(setup)

        self.assertIn(invoice_model.invoice_number, str(invoice_model))
        self.assertIn(invoice_model.get_invoice_status_display(), str(invoice_model))

        title = invoice_model.generate_descriptive_title()
        self.assertTrue(title.startswith("Invoice "))
        self.assertIn("Invoice", title)
        self.assertIn(invoice_model.invoice_number, title)
        self.assertIn(setup["customer_model"].customer_name, title)
        self.assertIn(invoice_model.get_invoice_status_display(), title)

        html_helpers = [
            invoice_model.get_html_id,
            invoice_model.get_html_amount_due_id,
            invoice_model.get_html_amount_paid_id,
            invoice_model.get_html_form_id,
            invoice_model.get_mark_as_draft_html_id,
            invoice_model.get_mark_as_review_html_id,
            invoice_model.get_mark_as_approved_html_id,
            invoice_model.get_mark_as_paid_html_id,
            invoice_model.get_mark_as_void_html_id,
            invoice_model.get_mark_as_canceled_html_id,
        ]
        for helper in html_helpers:
            self.assertIn(str(invoice_model.uuid), helper())

        message_helpers = [
            invoice_model.get_mark_as_draft_message,
            invoice_model.get_mark_as_review_message,
            invoice_model.get_mark_as_approved_message,
            invoice_model.get_mark_as_paid_message,
            invoice_model.get_mark_as_void_message,
            invoice_model.get_mark_as_canceled_message,
        ]
        for helper in message_helpers:
            self.assertIn(invoice_model.invoice_number, helper())

    def test_mark_as_review_emits_invoice_status_in_review_signal(self):
        setup = self.create_entity_setup(name="API Invoice Review Signal Entity")
        invoice_model = self.migrate_service_item(self.create_invoice(setup), setup)
        calls = self.collect_signal_calls(invoice_status_in_review)

        invoice_model.mark_as_review(commit=True, date_in_review=date(2025, 1, 16))

        self.assert_signal_received_once(calls, invoice_model, commit=True)

    def test_mark_as_draft_emits_invoice_status_draft_signal(self):
        setup = self.create_entity_setup(name="API Invoice Draft Signal Entity")
        invoice_model = self.make_review_invoice(setup)
        calls = self.collect_signal_calls(invoice_status_draft)

        invoice_model.mark_as_draft(draft_date=date(2025, 1, 17), commit=True)

        self.assert_signal_received_once(calls, invoice_model, commit=True)

    def test_mark_as_approved_emits_invoice_status_approved_signal(self):
        setup = self.create_entity_setup(name="API Invoice Approved Signal Entity")
        invoice_model = self.make_review_invoice(setup)
        calls = self.collect_signal_calls(invoice_status_approved)

        invoice_model.mark_as_approved(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_approved=date(2025, 1, 17),
            commit=True,
        )

        self.assert_signal_received_once(calls, invoice_model, commit=True)

    def test_mark_as_paid_emits_invoice_status_paid_signal(self):
        setup = self.create_entity_setup(name="API Invoice Paid Signal Entity")
        invoice_model = self.make_approved_invoice(setup)
        calls = self.collect_signal_calls(invoice_status_paid)

        invoice_model.mark_as_paid(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_paid=date(2025, 1, 18),
            commit=True,
        )

        self.assert_signal_received_once(calls, invoice_model, commit=True)

    def test_mark_as_canceled_emits_invoice_status_canceled_signal(self):
        setup = self.create_entity_setup(name="API Invoice Canceled Signal Entity")
        invoice_model = self.create_invoice(setup)
        calls = self.collect_signal_calls(invoice_status_canceled)

        invoice_model.mark_as_canceled(commit=True, date_canceled=date(2025, 1, 20))

        self.assert_signal_received_once(calls, invoice_model, commit=True)

    def test_mark_as_void_emits_invoice_status_void_signal(self):
        setup = self.create_entity_setup(name="API Invoice Void Signal Entity")
        invoice_model = self.make_approved_invoice(setup)
        calls = self.collect_signal_calls(invoice_status_void)

        invoice_model.mark_as_void(
            entity_slug=setup["entity_model"].slug,
            user_model=self.user,
            date_void=date(2025, 1, 19),
            commit=True,
        )

        self.assert_signal_received_once(calls, invoice_model, commit=True)
