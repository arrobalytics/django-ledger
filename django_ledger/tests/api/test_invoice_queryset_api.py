"""
High-level API tests for InvoiceModel queryset and manager behavior.
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
from django_ledger.models.invoice import InvoiceModelValidationError
from django_ledger.models.items import ItemModel


class InvoiceQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_invoice_queryset_admin",
            email="api-invoice-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_invoice_queryset_manager",
            email="api-invoice-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_invoice_queryset_other_admin",
            email="api-invoice-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_invoice_queryset_unrelated",
            email="api-invoice-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_invoice_queryset_superuser",
            email="api-invoice-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Invoice Queryset Entity", admin_user=None, manager_user=None):
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
            role=ASSET_CA_CASH,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        receivable_account = coa_model.create_account(
            code="1210",
            name=f"{name} Receivable Account",
            role=ASSET_CA_RECEIVABLES,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        deferred_account = coa_model.create_account(
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
            description=f"{name} Customer description",
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
            "cash_account": cash_account,
            "receivable_account": receivable_account,
            "deferred_account": deferred_account,
            "customer_model": customer_model,
            "service_item": service_item,
        }

    def create_invoice(self, setup, *, date_draft=date(2026, 1, 15)):
        invoice_model = InvoiceModel(
            customer=setup["customer_model"],
            terms=InvoiceModel.TERMS_NET_30,
            cash_account=setup["cash_account"],
            prepaid_account=setup["receivable_account"],
            unearned_account=setup["deferred_account"],
        )
        _ledger_model, invoice_model = invoice_model.configure(
            entity_slug=setup["entity_model"],
            user_model=self.admin_user,
            date_draft=date_draft,
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def migrate_service_item(self, invoice_model, setup, *, quantity="2.00", unit_cost="50.00"):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        invoice_model.migrate_itemtxs(
            itemtxs={
                setup["service_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "total_amount": quantity * unit_cost,
                }
            },
            operation=InvoiceModel.ITEMIZE_REPLACE,
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def move_to_review(self, invoice_model, setup):
        invoice_model = self.migrate_service_item(invoice_model, setup)
        invoice_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        invoice_model.refresh_from_db()
        return invoice_model

    def move_to_approved(self, invoice_model, setup):
        invoice_model = self.move_to_review(invoice_model, setup)
        invoice_model.mark_as_approved(
            entity_slug=setup["entity_model"],
            user_model=self.admin_user,
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def move_to_paid(self, invoice_model, setup):
        invoice_model = self.move_to_approved(invoice_model, setup)
        invoice_model.mark_as_paid(
            entity_slug=setup["entity_model"],
            user_model=self.admin_user,
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def move_to_void(self, invoice_model, setup):
        invoice_model = self.move_to_approved(invoice_model, setup)
        invoice_model.mark_as_void(
            entity_slug=setup["entity_model"],
            user_model=self.admin_user,
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def move_to_canceled(self, invoice_model):
        invoice_model.mark_as_canceled(date_canceled=date(2026, 1, 20), commit=True)
        invoice_model.refresh_from_db()
        return invoice_model

    def assert_invoice_uuids(self, queryset, expected_invoices):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {invoice_model.uuid for invoice_model in expected_invoices},
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API Invoice Queryset Entity A")
        other_setup = self.create_entity_setup(
            name="API Invoice Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        invoice_model = self.create_invoice(setup)
        self.create_invoice(other_setup)
        entity_model = setup["entity_model"]

        self.assert_invoice_uuids(InvoiceModel.objects.for_entity(entity_model), [invoice_model])
        self.assert_invoice_uuids(InvoiceModel.objects.for_entity(entity_model.slug), [invoice_model])
        self.assert_invoice_uuids(InvoiceModel.objects.for_entity(entity_model.uuid), [invoice_model])

    def test_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_invoice(self.create_entity_setup())

        with self.assertRaises(InvoiceModelValidationError):
            InvoiceModel.objects.for_entity(object())

        self.assertFalse(InvoiceModel.objects.for_entity("missing-invoice-entity-slug").exists())

    def test_for_user_scopes_to_authorized_users_and_superuser(self):
        setup = self.create_entity_setup(
            name="API Invoice Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_setup = self.create_entity_setup(
            name="API Invoice Queryset Other Access Entity",
            admin_user=self.other_admin_user,
        )
        invoice_model = self.create_invoice(setup)
        other_invoice_model = self.create_invoice(other_setup)

        self.assert_invoice_uuids(InvoiceModel.objects.all().for_user(self.admin_user), [invoice_model])
        self.assert_invoice_uuids(InvoiceModel.objects.all().for_user(self.manager_user), [invoice_model])
        self.assertFalse(InvoiceModel.objects.all().for_user(self.unrelated_user).exists())
        self.assert_invoice_uuids(
            InvoiceModel.objects.all().for_user(self.superuser),
            [invoice_model, other_invoice_model],
        )

    def test_status_filters_return_matching_invoices(self):
        setup = self.create_entity_setup(name="API Invoice Queryset Status Entity")
        draft_invoice = self.create_invoice(setup)
        review_invoice = self.move_to_review(self.create_invoice(setup), setup)
        approved_invoice = self.move_to_approved(self.create_invoice(setup), setup)
        paid_invoice = self.move_to_paid(self.create_invoice(setup), setup)
        void_invoice = self.move_to_void(self.create_invoice(setup), setup)
        canceled_invoice = self.move_to_canceled(self.create_invoice(setup))

        invoices_qs = InvoiceModel.objects.for_entity(setup["entity_model"])

        self.assert_invoice_uuids(invoices_qs.draft(), [draft_invoice])
        self.assert_invoice_uuids(invoices_qs.in_review(), [review_invoice])
        self.assert_invoice_uuids(invoices_qs.approved(), [approved_invoice])
        self.assert_invoice_uuids(invoices_qs.paid(), [paid_invoice])
        self.assert_invoice_uuids(invoices_qs.void(), [void_invoice])
        self.assert_invoice_uuids(invoices_qs.canceled(), [canceled_invoice])

    def test_semantic_filters_return_active_unpaid_and_overdue_invoices(self):
        setup = self.create_entity_setup(name="API Invoice Queryset Semantic Entity")
        draft_invoice = self.create_invoice(setup)
        approved_invoice = self.move_to_approved(self.create_invoice(setup), setup)
        paid_invoice = self.move_to_paid(self.create_invoice(setup), setup)
        void_invoice = self.move_to_void(self.create_invoice(setup), setup)

        overdue_invoice = self.create_invoice(setup)
        overdue_invoice.date_due = date(2000, 1, 1)
        overdue_invoice.save(update_fields=["date_due", "updated"])

        future_due_invoice = self.create_invoice(setup)
        future_due_invoice.date_due = date(2099, 1, 1)
        future_due_invoice.save(update_fields=["date_due", "updated"])

        invoices_qs = InvoiceModel.objects.for_entity(setup["entity_model"])

        self.assert_invoice_uuids(invoices_qs.active(), [approved_invoice, paid_invoice])
        self.assert_invoice_uuids(invoices_qs.unpaid(), [approved_invoice])
        self.assertTrue(invoices_qs.overdue().filter(uuid=overdue_invoice.uuid).exists())
        self.assertFalse(invoices_qs.overdue().filter(uuid=future_due_invoice.uuid).exists())
        self.assertFalse(invoices_qs.active().filter(uuid=draft_invoice.uuid).exists())
        self.assertFalse(invoices_qs.active().filter(uuid=void_invoice.uuid).exists())
