"""
High-level API behavior tests for QuerySet and Manager contracts.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import (
    AccountModel,
    BillModel,
    EstimateModel,
    InvoiceModel,
    ItemTransactionModel,
    PurchaseOrderModel,
)
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.vendor import VendorModel


class QuerySetContractsHighLevelAPITest(TestCase):
    """
    High-level behavior tests for public QuerySet and Manager contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document the public filtering API that should remain stable
    across swappable-model refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_queryset_contract_user",
            email="api-queryset-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API QuerySet Contract Entity"):
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

        inactive_cash_account = coa_model.create_account(
            code="1020",
            name=f"{name} Inactive Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=False,
        )

        uom_model = entity_model.create_uom(
            name=f"{name} Unit",
            unit_abbr="qs",
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

        inactive_customer = CustomerModel(
            customer_name=f"{name} Inactive Customer",
            entity_model=entity_model,
            description=f"{name} Inactive Customer description",
            active=False,
            hidden=False,
        )
        inactive_customer.full_clean()
        inactive_customer.save()

        hidden_customer = CustomerModel(
            customer_name=f"{name} Hidden Customer",
            entity_model=entity_model,
            description=f"{name} Hidden Customer description",
            active=True,
            hidden=True,
        )
        hidden_customer.full_clean()
        hidden_customer.save()

        vendor_model = VendorModel(
            vendor_name=f"{name} Vendor",
            entity_model=entity_model,
            description=f"{name} Vendor description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()

        inactive_vendor = VendorModel(
            vendor_name=f"{name} Inactive Vendor",
            entity_model=entity_model,
            description=f"{name} Inactive Vendor description",
            active=False,
            hidden=False,
        )
        inactive_vendor.full_clean()
        inactive_vendor.save()

        hidden_vendor = VendorModel(
            vendor_name=f"{name} Hidden Vendor",
            entity_model=entity_model,
            description=f"{name} Hidden Vendor description",
            active=True,
            hidden=True,
        )
        hidden_vendor.full_clean()
        hidden_vendor.save()

        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )

        product_item = entity_model.create_item_product(
            name=f"{name} Product Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
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
            "inactive_cash_account": inactive_cash_account,
            "uom_model": uom_model,
            "customer_model": customer_model,
            "inactive_customer": inactive_customer,
            "hidden_customer": hidden_customer,
            "vendor_model": vendor_model,
            "inactive_vendor": inactive_vendor,
            "hidden_vendor": hidden_vendor,
            "service_item": service_item,
            "product_item": product_item,
            "inventory_item": inventory_item,
            "expense_item": expense_item,
        }

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
            estimate_title="API QuerySet Estimate",
            commit=True,
        )

        return estimate_model

    def create_purchase_order(self, setup):
        po_model = PurchaseOrderModel()

        po_model.configure(
            entity_slug=setup["entity_model"],
            po_title="API QuerySet Purchase Order",
            user_model=self.user,
            draft_date=date(2026, 1, 15),
            commit=True,
        )

        return po_model

    def migrate_bill_item(self, bill_model, setup):
        quantity = Decimal("2.00")
        unit_cost = Decimal("50.00")

        bill_model.migrate_itemtxs(
            itemtxs={
                setup["expense_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "total_amount": quantity * unit_cost,
                }
            },
            operation=BillModel.ITEMIZE_REPLACE,
            commit=True,
        )

        bill_model.refresh_from_db()
        return bill_model

    def migrate_invoice_item(self, invoice_model, setup):
        quantity = Decimal("2.00")
        unit_cost = Decimal("75.00")

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

    def migrate_estimate_item(self, estimate_model, setup):
        quantity = Decimal("2.00")
        unit_cost = Decimal("30.00")
        unit_revenue = Decimal("75.00")

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

    def migrate_purchase_order_item(self, po_model, setup):
        quantity = Decimal("3.00")
        unit_cost = Decimal("20.00")

        po_model.migrate_itemtxs(
            itemtxs={
                setup["inventory_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "total_amount": quantity * unit_cost,
                }
            },
            operation=PurchaseOrderModel.ITEMIZE_REPLACE,
            commit=True,
        )

        po_model.refresh_from_db()
        return po_model

    def test_account_queryset_contracts(self):
        setup = self.create_entity_setup()
        accounts_qs = AccountModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(accounts_qs.not_coa_root().filter(uuid=setup["cash_account"].uuid).exists())
        self.assertFalse(accounts_qs.is_coa_root().filter(uuid=setup["cash_account"].uuid).exists())

        self.assertTrue(accounts_qs.available().filter(uuid=setup["cash_account"].uuid).exists())
        self.assertFalse(accounts_qs.available().filter(uuid=setup["inactive_cash_account"].uuid).exists())

        self.assertTrue(accounts_qs.is_role_default().filter(uuid=setup["cash_account"].uuid).exists())
        self.assertTrue(accounts_qs.cash().filter(uuid=setup["cash_account"].uuid).exists())
        self.assertTrue(accounts_qs.expenses().filter(uuid=setup["expense_account"].uuid).exists())

    def test_customer_and_vendor_queryset_contracts(self):
        setup = self.create_entity_setup()

        customers_qs = CustomerModel.objects.for_entity(setup["entity_model"])
        vendors_qs = VendorModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(customers_qs.active().filter(uuid=setup["customer_model"].uuid).exists())
        self.assertFalse(customers_qs.active().filter(uuid=setup["inactive_customer"].uuid).exists())
        self.assertTrue(customers_qs.inactive().filter(uuid=setup["inactive_customer"].uuid).exists())

        self.assertTrue(customers_qs.visible().filter(uuid=setup["customer_model"].uuid).exists())
        self.assertFalse(customers_qs.visible().filter(uuid=setup["hidden_customer"].uuid).exists())
        self.assertTrue(customers_qs.hidden().filter(uuid=setup["hidden_customer"].uuid).exists())

        self.assertTrue(vendors_qs.active().filter(uuid=setup["vendor_model"].uuid).exists())
        self.assertFalse(vendors_qs.active().filter(uuid=setup["inactive_vendor"].uuid).exists())
        self.assertTrue(vendors_qs.inactive().filter(uuid=setup["inactive_vendor"].uuid).exists())

        self.assertTrue(vendors_qs.visible().filter(uuid=setup["vendor_model"].uuid).exists())
        self.assertFalse(vendors_qs.visible().filter(uuid=setup["hidden_vendor"].uuid).exists())
        self.assertTrue(vendors_qs.hidden().filter(uuid=setup["hidden_vendor"].uuid).exists())

    def test_item_queryset_contracts(self):
        setup = self.create_entity_setup()

        items_qs = ItemModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(items_qs.services().filter(uuid=setup["service_item"].uuid).exists())
        self.assertTrue(items_qs.products().filter(uuid=setup["product_item"].uuid).exists())
        self.assertTrue(items_qs.inventory_all().filter(uuid=setup["inventory_item"].uuid).exists())
        self.assertTrue(items_qs.expenses().filter(uuid=setup["expense_item"].uuid).exists())

        invoice_items_qs = ItemModel.objects.for_invoice(setup["entity_model"])
        bill_items_qs = ItemModel.objects.for_bill(setup["entity_model"])

        self.assertTrue(invoice_items_qs.filter(uuid=setup["service_item"].uuid).exists())
        self.assertTrue(invoice_items_qs.filter(uuid=setup["product_item"].uuid).exists())
        self.assertFalse(invoice_items_qs.filter(uuid=setup["expense_item"].uuid).exists())

        self.assertTrue(bill_items_qs.filter(uuid=setup["expense_item"].uuid).exists())
        self.assertTrue(bill_items_qs.filter(uuid=setup["inventory_item"].uuid).exists())
        self.assertFalse(bill_items_qs.filter(uuid=setup["service_item"].uuid).exists())

    def test_bill_queryset_status_contracts(self):
        setup = self.create_entity_setup()

        draft_bill = self.create_bill(setup)

        approved_bill = self.create_bill(setup)
        approved_bill = self.migrate_bill_item(approved_bill, setup)
        approved_bill.mark_as_review(commit=True)
        approved_bill.mark_as_approved(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        approved_bill.refresh_from_db()

        paid_bill = self.create_bill(setup)
        paid_bill = self.migrate_bill_item(paid_bill, setup)
        paid_bill.mark_as_review(commit=True)
        paid_bill.mark_as_approved(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        paid_bill.mark_as_paid(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        paid_bill.refresh_from_db()

        bills_qs = BillModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(bills_qs.draft().filter(uuid=draft_bill.uuid).exists())
        self.assertTrue(bills_qs.approved().filter(uuid=approved_bill.uuid).exists())
        self.assertTrue(bills_qs.paid().filter(uuid=paid_bill.uuid).exists())
        self.assertTrue(bills_qs.active().filter(uuid=approved_bill.uuid).exists())
        self.assertTrue(bills_qs.active().filter(uuid=paid_bill.uuid).exists())

    def test_invoice_queryset_status_contracts(self):
        setup = self.create_entity_setup()

        draft_invoice = self.create_invoice(setup)

        approved_invoice = self.create_invoice(setup)
        approved_invoice = self.migrate_invoice_item(approved_invoice, setup)
        approved_invoice.mark_as_review(commit=True)
        approved_invoice.mark_as_approved(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        approved_invoice.refresh_from_db()

        paid_invoice = self.create_invoice(setup)
        paid_invoice = self.migrate_invoice_item(paid_invoice, setup)
        paid_invoice.mark_as_review(commit=True)
        paid_invoice.mark_as_approved(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        paid_invoice.mark_as_paid(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            commit=True,
        )
        paid_invoice.refresh_from_db()

        invoices_qs = InvoiceModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(invoices_qs.draft().filter(uuid=draft_invoice.uuid).exists())
        self.assertTrue(invoices_qs.approved().filter(uuid=approved_invoice.uuid).exists())
        self.assertTrue(invoices_qs.paid().filter(uuid=paid_invoice.uuid).exists())
        self.assertTrue(invoices_qs.active().filter(uuid=approved_invoice.uuid).exists())
        self.assertTrue(invoices_qs.active().filter(uuid=paid_invoice.uuid).exists())

    def test_estimate_queryset_status_contracts(self):
        setup = self.create_entity_setup()

        draft_estimate = self.create_estimate(setup)

        approved_estimate = self.create_estimate(setup)
        approved_estimate = self.migrate_estimate_item(approved_estimate, setup)
        approved_estimate.mark_as_review(commit=True)
        approved_estimate.mark_as_approved(commit=True)
        approved_estimate.refresh_from_db()

        completed_estimate = self.create_estimate(setup)
        completed_estimate = self.migrate_estimate_item(completed_estimate, setup)
        completed_estimate.mark_as_review(commit=True)
        completed_estimate.mark_as_approved(commit=True)
        completed_estimate.mark_as_completed(commit=True)
        completed_estimate.refresh_from_db()

        estimates_qs = EstimateModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(estimates_qs.draft().filter(uuid=draft_estimate.uuid).exists())
        self.assertTrue(estimates_qs.approved().filter(uuid=approved_estimate.uuid).exists())
        self.assertTrue(estimates_qs.approved().filter(uuid=completed_estimate.uuid).exists())
        self.assertTrue(estimates_qs.contracts().filter(uuid=approved_estimate.uuid).exists())
        self.assertTrue(estimates_qs.contracts().filter(uuid=completed_estimate.uuid).exists())
        self.assertTrue(estimates_qs.estimates().filter(uuid=draft_estimate.uuid).exists())
        self.assertFalse(estimates_qs.estimates().filter(uuid=approved_estimate.uuid).exists())

    def test_purchase_order_queryset_status_contracts(self):
        setup = self.create_entity_setup()

        draft_po = self.create_purchase_order(setup)

        approved_po = self.create_purchase_order(setup)
        approved_po = self.migrate_purchase_order_item(approved_po, setup)
        approved_po.mark_as_review(commit=True)
        approved_po.mark_as_approved(commit=True)
        approved_po.refresh_from_db()

        purchase_orders_qs = PurchaseOrderModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(purchase_orders_qs.draft().filter(uuid=draft_po.uuid).exists())
        self.assertTrue(purchase_orders_qs.approved().filter(uuid=approved_po.uuid).exists())
        self.assertTrue(purchase_orders_qs.active().filter(uuid=approved_po.uuid).exists())
        self.assertFalse(purchase_orders_qs.fulfilled().filter(uuid=approved_po.uuid).exists())
