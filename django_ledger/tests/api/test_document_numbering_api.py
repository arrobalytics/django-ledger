"""
High-level API behavior tests for document and catalog numbering contracts.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import (
    BillModel,
    EstimateModel,
    InvoiceModel,
    PurchaseOrderModel,
)
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.vendor import VendorModel


class DocumentNumberingHighLevelAPITest(TestCase):
    """
    High-level behavior tests for entity-scoped number generation.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic numbering contracts that should remain
    true across swappable-model refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_document_numbering_contract_user",
            email="api-document-numbering-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_with_numbering_setup(self, *, name="API Numbering Contract Entity"):
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
            name=f"{name} Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        receivable_account = coa_model.create_account(
            code="1210",
            name=f"{name} Receivable Account",
            role="asset_ca_recv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        prepaid_account = coa_model.create_account(
            code="1310",
            name=f"{name} Prepaid Account",
            role="asset_ca_prepaid",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        inventory_account = coa_model.create_account(
            code="1510",
            name=f"{name} Inventory Account",
            role="asset_ca_inv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        accounts_payable = coa_model.create_account(
            code="2010",
            name=f"{name} Accounts Payable",
            role="lia_cl_acc_payable",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        unearned_account = coa_model.create_account(
            code="2310",
            name=f"{name} Unearned Revenue Account",
            role="lia_cl_def_rev",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        cogs_account = coa_model.create_account(
            code="5010",
            name=f"{name} COGS Account",
            role="cogs_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        earnings_account = coa_model.create_account(
            code="4010",
            name=f"{name} Earnings Account",
            role="in_operational",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        uom_model = entity_model.create_uom(
            name=f"{name} Unit",
            unit_abbr="num",
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

        vendor_model = VendorModel(
            vendor_name=f"{name} Vendor",
            entity_model=entity_model,
            description=f"{name} Vendor description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()

        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
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

        inventory_item = entity_model.create_item_inventory(
            name=f"{name} Inventory Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=inventory_account,
            coa_model=coa_model,
            commit=True,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "receivable_account": receivable_account,
            "prepaid_account": prepaid_account,
            "inventory_account": inventory_account,
            "accounts_payable": accounts_payable,
            "unearned_account": unearned_account,
            "cogs_account": cogs_account,
            "earnings_account": earnings_account,
            "expense_account": expense_account,
            "uom_model": uom_model,
            "customer_model": customer_model,
            "vendor_model": vendor_model,
            "service_item": service_item,
            "expense_item": expense_item,
            "inventory_item": inventory_item,
        }

    def create_customer(self, setup, *, suffix):
        customer_model = CustomerModel(
            customer_name=f"API Numbering Customer {suffix}",
            entity_model=setup["entity_model"],
            description=f"API Numbering Customer {suffix} description",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        return customer_model

    def create_vendor(self, setup, *, suffix):
        vendor_model = VendorModel(
            vendor_name=f"API Numbering Vendor {suffix}",
            entity_model=setup["entity_model"],
            description=f"API Numbering Vendor {suffix} description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()
        return vendor_model

    def create_service_item(self, setup, *, suffix):
        return setup["entity_model"].create_item_service(
            name=f"API Numbering Service Item {suffix}",
            uom_model=setup["uom_model"],
            coa_model=setup["coa_model"],
            commit=True,
        )

    def create_bill(self, setup):
        bill_model = BillModel(
            vendor=setup["vendor_model"],
            cash_account=setup["cash_account"],
            prepaid_account=setup["prepaid_account"],
            unearned_account=setup["accounts_payable"],
        )

        _ledger_model, bill_model = bill_model.configure(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            date_draft=date(2026, 1, 15),
            commit=True,
        )

        return bill_model

    def create_invoice(self, setup):
        invoice_model = InvoiceModel(
            customer=setup["customer_model"],
            cash_account=setup["cash_account"],
            prepaid_account=setup["receivable_account"],
            unearned_account=setup["unearned_account"],
        )

        _ledger_model, invoice_model = invoice_model.configure(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            date_draft=date(2026, 1, 15),
            commit=True,
        )

        return invoice_model

    def create_estimate(self, setup):
        estimate_model = EstimateModel(
            terms=EstimateModel.CONTRACT_TERMS_FIXED,
        )

        estimate_model.configure(
            entity_slug=setup["entity_model"],
            customer_model=setup["customer_model"],
            user_model=self.user,
            date_draft=date(2026, 1, 15),
            estimate_title="API Numbering Estimate",
            commit=True,
        )

        return estimate_model

    def create_purchase_order(self, setup):
        po_model = PurchaseOrderModel()

        po_model.configure(
            entity_slug=setup["entity_model"],
            po_title="API Numbering Purchase Order",
            user_model=self.user,
            draft_date=date(2026, 1, 15),
            commit=True,
        )

        return po_model

    def test_customer_vendor_and_item_numbers_are_generated(self):
        setup = self.create_entity_with_numbering_setup()

        self.assertTrue(setup["customer_model"].customer_number)
        self.assertTrue(setup["vendor_model"].vendor_number)
        self.assertTrue(setup["service_item"].item_number)
        self.assertTrue(setup["expense_item"].item_number)
        self.assertTrue(setup["inventory_item"].item_number)

    def test_customer_vendor_and_item_numbers_are_unique_within_entity(self):
        setup = self.create_entity_with_numbering_setup()

        customer_a = self.create_customer(setup, suffix="A")
        customer_b = self.create_customer(setup, suffix="B")

        vendor_a = self.create_vendor(setup, suffix="A")
        vendor_b = self.create_vendor(setup, suffix="B")

        item_a = self.create_service_item(setup, suffix="A")
        item_b = self.create_service_item(setup, suffix="B")

        self.assertNotEqual(customer_a.customer_number, customer_b.customer_number)
        self.assertNotEqual(vendor_a.vendor_number, vendor_b.vendor_number)
        self.assertNotEqual(item_a.item_number, item_b.item_number)

    def test_bill_invoice_estimate_and_po_numbers_are_generated_on_configure(self):
        setup = self.create_entity_with_numbering_setup()

        bill_model = self.create_bill(setup)
        invoice_model = self.create_invoice(setup)
        estimate_model = self.create_estimate(setup)
        po_model = self.create_purchase_order(setup)

        self.assertTrue(bill_model.bill_number)
        self.assertTrue(invoice_model.invoice_number)
        self.assertTrue(estimate_model.estimate_number)
        self.assertTrue(po_model.po_number)

    def test_document_numbers_are_unique_within_entity(self):
        setup = self.create_entity_with_numbering_setup()

        bill_a = self.create_bill(setup)
        bill_b = self.create_bill(setup)

        invoice_a = self.create_invoice(setup)
        invoice_b = self.create_invoice(setup)

        estimate_a = self.create_estimate(setup)
        estimate_b = self.create_estimate(setup)

        po_a = self.create_purchase_order(setup)
        po_b = self.create_purchase_order(setup)

        self.assertNotEqual(bill_a.bill_number, bill_b.bill_number)
        self.assertNotEqual(invoice_a.invoice_number, invoice_b.invoice_number)
        self.assertNotEqual(estimate_a.estimate_number, estimate_b.estimate_number)
        self.assertNotEqual(po_a.po_number, po_b.po_number)

    def test_number_generation_is_scoped_by_entity(self):
        setup_a = self.create_entity_with_numbering_setup(name="API Numbering Entity A")
        setup_b = self.create_entity_with_numbering_setup(name="API Numbering Entity B")

        bill_a = self.create_bill(setup_a)
        bill_b = self.create_bill(setup_b)

        invoice_a = self.create_invoice(setup_a)
        invoice_b = self.create_invoice(setup_b)

        estimate_a = self.create_estimate(setup_a)
        estimate_b = self.create_estimate(setup_b)

        po_a = self.create_purchase_order(setup_a)
        po_b = self.create_purchase_order(setup_b)

        self.assertEqual(bill_a.bill_number, bill_b.bill_number)
        self.assertEqual(invoice_a.invoice_number, invoice_b.invoice_number)
        self.assertEqual(estimate_a.estimate_number, estimate_b.estimate_number)
        self.assertEqual(po_a.po_number, po_b.po_number)
