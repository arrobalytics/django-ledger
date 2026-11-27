"""
High-level API behavior tests for EntityModel document factories.

These tests exercise EntityModel.create_* convenience APIs directly, rather
than lower-level document configure hooks.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import BillModel, EstimateModel, InvoiceModel, PurchaseOrderModel
from django_ledger.models.entity import EntityModel, EntityModelValidationError


class EntityFactoryAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_entity_factory_user",
            email="api-entity-factory-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Entity Factory Entity"):
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

        cash_account = coa_model.create_account(
            code="1010",
            name=f"{name} Cash",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        prepaid_account = coa_model.create_account(
            code="1310",
            name=f"{name} Prepaid",
            role="asset_ca_prepaid",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        payable_account = coa_model.create_account(
            code="2010",
            name=f"{name} Accounts Payable",
            role="lia_cl_acc_payable",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        receivable_account = coa_model.create_account(
            code="1210",
            name=f"{name} Receivable",
            role="asset_ca_recv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        deferred_revenue_account = coa_model.create_account(
            code="2310",
            name=f"{name} Deferred Revenue",
            role="lia_cl_def_rev",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        customer_model = entity_model.create_customer(
            {
                "customer_name": f"{name} Customer",
                "description": f"{name} customer",
                "active": True,
                "hidden": False,
            },
            commit=True,
        )
        vendor_model = entity_model.create_vendor(
            {
                "vendor_name": f"{name} Vendor",
                "description": f"{name} vendor",
                "active": True,
                "hidden": False,
            },
            commit=True,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "prepaid_account": prepaid_account,
            "payable_account": payable_account,
            "receivable_account": receivable_account,
            "deferred_revenue_account": deferred_revenue_account,
            "customer_model": customer_model,
            "vendor_model": vendor_model,
        }

    def test_document_factories_create_draft_documents_for_entity(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]

        bill_model = entity_model.create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_NET_30,
            date_draft=date(2026, 1, 15),
            ledger_name="API Factory Bill Ledger",
            commit=True,
        )
        invoice_model = entity_model.create_invoice(
            customer_model=setup["customer_model"],
            terms=InvoiceModel.TERMS_NET_30,
            date_draft=date(2026, 1, 15),
            ledger_name="API Factory Invoice Ledger",
            commit=True,
        )
        estimate_model = entity_model.create_estimate(
            estimate_title="API Factory Estimate",
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=setup["customer_model"],
            commit=True,
        )
        po_model = entity_model.create_purchase_order(
            po_title="API Factory Purchase Order",
            date_draft=date(2026, 1, 15),
            commit=True,
        )

        self.assertTrue(bill_model.is_draft())
        self.assertEqual(bill_model.vendor_id, setup["vendor_model"].uuid)
        self.assertEqual(bill_model.ledger.entity_id, entity_model.uuid)
        self.assertEqual(bill_model.ledger.name, "API Factory Bill Ledger")
        self.assertEqual(bill_model.cash_account_id, setup["cash_account"].uuid)
        self.assertEqual(bill_model.prepaid_account_id, setup["prepaid_account"].uuid)
        self.assertEqual(bill_model.unearned_account_id, setup["payable_account"].uuid)
        self.assertTrue(bill_model.bill_number)

        self.assertTrue(invoice_model.is_draft())
        self.assertEqual(invoice_model.customer_id, setup["customer_model"].uuid)
        self.assertEqual(invoice_model.ledger.entity_id, entity_model.uuid)
        self.assertEqual(invoice_model.ledger.name, "API Factory Invoice Ledger")
        self.assertEqual(invoice_model.cash_account_id, setup["cash_account"].uuid)
        self.assertEqual(invoice_model.prepaid_account_id, setup["receivable_account"].uuid)
        self.assertEqual(invoice_model.unearned_account_id, setup["deferred_revenue_account"].uuid)
        self.assertTrue(invoice_model.invoice_number)

        self.assertTrue(estimate_model.is_draft())
        self.assertEqual(estimate_model.entity_id, entity_model.uuid)
        self.assertEqual(estimate_model.customer_id, setup["customer_model"].uuid)
        self.assertEqual(estimate_model.title, "API Factory Estimate")
        self.assertTrue(estimate_model.estimate_number)

        self.assertTrue(po_model.is_draft())
        self.assertEqual(po_model.entity_id, entity_model.uuid)
        self.assertEqual(po_model.po_title, "API Factory Purchase Order")
        self.assertEqual(po_model.date_draft, date(2026, 1, 15))
        self.assertTrue(po_model.po_number)

    def test_bill_factory_accepts_vendor_uuid_and_number(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        vendor_model = setup["vendor_model"]

        bill_from_uuid = entity_model.create_bill(
            vendor_model=vendor_model.uuid,
            terms=BillModel.TERMS_NET_30,
            commit=True,
        )
        bill_from_number = entity_model.create_bill(
            vendor_model=vendor_model.vendor_number,
            terms=BillModel.TERMS_NET_30,
            commit=True,
        )

        self.assertEqual(bill_from_uuid.vendor_id, vendor_model.uuid)
        self.assertEqual(bill_from_number.vendor_id, vendor_model.uuid)
        self.assertTrue(bill_from_uuid.bill_number)
        self.assertTrue(bill_from_number.bill_number)

    def test_invoice_and_estimate_factories_accept_customer_uuid_and_number(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        customer_model = setup["customer_model"]

        invoice_from_uuid = entity_model.create_invoice(
            customer_model=customer_model.uuid,
            terms=InvoiceModel.TERMS_NET_30,
            commit=True,
        )
        invoice_from_number = entity_model.create_invoice(
            customer_model=customer_model.customer_number,
            terms=InvoiceModel.TERMS_NET_30,
            commit=True,
        )
        estimate_from_uuid = entity_model.create_estimate(
            estimate_title="API Estimate From UUID",
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=customer_model.uuid,
            commit=True,
        )
        estimate_from_number = entity_model.create_estimate(
            estimate_title="API Estimate From Number",
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=customer_model.customer_number,
            commit=True,
        )

        self.assertEqual(invoice_from_uuid.customer_id, customer_model.uuid)
        self.assertEqual(invoice_from_number.customer_id, customer_model.uuid)
        self.assertTrue(invoice_from_uuid.invoice_number)
        self.assertTrue(invoice_from_number.invoice_number)

        self.assertEqual(estimate_from_uuid.customer_id, customer_model.uuid)
        self.assertEqual(estimate_from_number.customer_id, customer_model.uuid)
        self.assertTrue(estimate_from_uuid.estimate_number)
        self.assertTrue(estimate_from_number.estimate_number)

    def test_bill_and_invoice_factories_respect_explicit_account_arguments(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]
        coa_model = setup["coa_model"]

        explicit_bill_cash = coa_model.create_account(
            code="1020",
            name="API Explicit Bill Cash",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )
        explicit_bill_prepaid = coa_model.create_account(
            code="1320",
            name="API Explicit Bill Prepaid",
            role="asset_ca_prepaid",
            balance_type="debit",
            active=True,
        )
        explicit_bill_payable = coa_model.create_account(
            code="2020",
            name="API Explicit Bill Payable",
            role="lia_cl_acc_payable",
            balance_type="credit",
            active=True,
        )
        explicit_invoice_cash = coa_model.create_account(
            code="1030",
            name="API Explicit Invoice Cash",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )
        explicit_invoice_receivable = coa_model.create_account(
            code="1220",
            name="API Explicit Invoice Receivable",
            role="asset_ca_recv",
            balance_type="debit",
            active=True,
        )
        explicit_invoice_deferred = coa_model.create_account(
            code="2320",
            name="API Explicit Invoice Deferred",
            role="lia_cl_def_rev",
            balance_type="credit",
            active=True,
        )

        bill_model = entity_model.create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_NET_30,
            cash_account=explicit_bill_cash,
            prepaid_account=explicit_bill_prepaid,
            payable_account=explicit_bill_payable,
            commit=True,
        )
        invoice_model = entity_model.create_invoice(
            customer_model=setup["customer_model"],
            terms=InvoiceModel.TERMS_NET_30,
            cash_account=explicit_invoice_cash,
            prepaid_account=explicit_invoice_receivable,
            payable_account=explicit_invoice_deferred,
            commit=True,
        )

        self.assertEqual(bill_model.cash_account_id, explicit_bill_cash.uuid)
        self.assertEqual(bill_model.prepaid_account_id, explicit_bill_prepaid.uuid)
        self.assertEqual(bill_model.unearned_account_id, explicit_bill_payable.uuid)

        self.assertEqual(invoice_model.cash_account_id, explicit_invoice_cash.uuid)
        self.assertEqual(invoice_model.prepaid_account_id, explicit_invoice_receivable.uuid)
        self.assertEqual(invoice_model.unearned_account_id, explicit_invoice_deferred.uuid)

    def test_document_factories_reject_cross_entity_parties(self):
        setup = self.create_entity_setup(name="API Factory Entity A")
        other_setup = self.create_entity_setup(name="API Factory Entity B")
        entity_model = setup["entity_model"]

        with self.assertRaises(EntityModelValidationError):
            entity_model.create_bill(
                vendor_model=other_setup["vendor_model"],
                terms=BillModel.TERMS_NET_30,
                commit=True,
            )

        with self.assertRaises(EntityModelValidationError):
            entity_model.create_invoice(
                customer_model=other_setup["customer_model"],
                terms=InvoiceModel.TERMS_NET_30,
                commit=True,
            )

        with self.assertRaises(EntityModelValidationError):
            entity_model.create_estimate(
                estimate_title="API Cross Entity Estimate",
                contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
                customer_model=other_setup["customer_model"],
                commit=True,
            )

    def test_document_getters_are_entity_scoped(self):
        setup = self.create_entity_setup(name="API Factory Getter Entity A")
        other_setup = self.create_entity_setup(name="API Factory Getter Entity B")

        bill_model = setup["entity_model"].create_bill(
            vendor_model=setup["vendor_model"],
            terms=BillModel.TERMS_NET_30,
            commit=True,
        )
        other_bill_model = other_setup["entity_model"].create_bill(
            vendor_model=other_setup["vendor_model"],
            terms=BillModel.TERMS_NET_30,
            commit=True,
        )

        invoice_model = setup["entity_model"].create_invoice(
            customer_model=setup["customer_model"],
            terms=InvoiceModel.TERMS_NET_30,
            commit=True,
        )
        other_invoice_model = other_setup["entity_model"].create_invoice(
            customer_model=other_setup["customer_model"],
            terms=InvoiceModel.TERMS_NET_30,
            commit=True,
        )

        estimate_model = setup["entity_model"].create_estimate(
            estimate_title="API Getter Estimate",
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=setup["customer_model"],
            commit=True,
        )
        other_estimate_model = other_setup["entity_model"].create_estimate(
            estimate_title="API Other Getter Estimate",
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=other_setup["customer_model"],
            commit=True,
        )

        po_model = setup["entity_model"].create_purchase_order(
            po_title="API Getter PO",
            commit=True,
        )
        other_po_model = other_setup["entity_model"].create_purchase_order(
            po_title="API Other Getter PO",
            commit=True,
        )

        self.assertTrue(setup["entity_model"].get_bills().filter(uuid=bill_model.uuid).exists())
        self.assertFalse(setup["entity_model"].get_bills().filter(uuid=other_bill_model.uuid).exists())

        self.assertTrue(setup["entity_model"].get_invoices().filter(uuid=invoice_model.uuid).exists())
        self.assertFalse(setup["entity_model"].get_invoices().filter(uuid=other_invoice_model.uuid).exists())

        self.assertTrue(setup["entity_model"].get_estimates().filter(uuid=estimate_model.uuid).exists())
        self.assertFalse(setup["entity_model"].get_estimates().filter(uuid=other_estimate_model.uuid).exists())

        self.assertTrue(setup["entity_model"].get_purchase_orders().filter(uuid=po_model.uuid).exists())
        self.assertFalse(setup["entity_model"].get_purchase_orders().filter(uuid=other_po_model.uuid).exists())
