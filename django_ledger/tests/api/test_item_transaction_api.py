"""
High-level API behavior tests for ItemTransactionModel document relationships.

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


class ItemTransactionHighLevelAPITest(TestCase):
    """
    High-level behavior tests for ItemTransactionModel as the shared document
    line-item model.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic relationship and amount invariants
    that should remain true across swappable-model refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_item_transaction_contract_user",
            email="api-item-transaction-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_with_document_setup(
        self,
        *,
        name="API Item Transaction Contract Entity",
    ):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        coa_model = entity_model.create_chart_of_accounts(
            coa_name="API Item Transaction Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        cash_account = coa_model.create_account(
            code="1010",
            name="API Item Transaction Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        receivable_account = coa_model.create_account(
            code="1210",
            name="API Item Transaction Receivable Account",
            role="asset_ca_recv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        prepaid_account = coa_model.create_account(
            code="1310",
            name="API Item Transaction Prepaid Account",
            role="asset_ca_prepaid",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        inventory_account = coa_model.create_account(
            code="1510",
            name="API Item Transaction Inventory Account",
            role="asset_ca_inv",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        accounts_payable = coa_model.create_account(
            code="2010",
            name="API Item Transaction Accounts Payable",
            role="lia_cl_acc_payable",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        unearned_account = coa_model.create_account(
            code="2310",
            name="API Item Transaction Unearned Revenue Account",
            role="lia_cl_def_rev",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        cogs_account = coa_model.create_account(
            code="5010",
            name="API Item Transaction COGS Account",
            role="cogs_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        earnings_account = coa_model.create_account(
            code="4010",
            name="API Item Transaction Earnings Account",
            role="in_operational",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )

        expense_account = coa_model.create_account(
            code="6010",
            name="API Item Transaction Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )

        uom_model = entity_model.create_uom(
            name="API Item Transaction Unit",
            unit_abbr="api-itx",
            active=True,
            commit=True,
        )

        customer_model = CustomerModel(
            customer_name="API Item Transaction Customer",
            entity_model=entity_model,
            description="API Item Transaction Customer description",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()

        vendor_model = VendorModel(
            vendor_name="API Item Transaction Vendor",
            entity_model=entity_model,
            description="API Item Transaction Vendor description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()

        service_item = entity_model.create_item_service(
            name="API Item Transaction Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )

        product_item = entity_model.create_item_product(
            name="API Item Transaction Product Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )

        inventory_item = entity_model.create_item_inventory(
            name="API Item Transaction Inventory Item",
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=inventory_account,
            coa_model=coa_model,
            commit=True,
        )

        expense_item = entity_model.create_item_expense(
            name="API Item Transaction Expense Item",
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
            "uom_model": uom_model,
            "customer_model": customer_model,
            "vendor_model": vendor_model,
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
            estimate_title="API Item Transaction Estimate",
            commit=True,
        )

        return estimate_model

    def create_purchase_order(self, setup):
        po_model = PurchaseOrderModel()

        po_model.configure(
            entity_slug=setup["entity_model"],
            po_title="API Item Transaction Purchase Order",
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

    def test_bill_item_transaction_belongs_only_to_bill_document(self):
        setup = self.create_entity_with_document_setup()
        bill_model = self.create_bill(setup)

        self.migrate_bill_item(bill_model, setup)

        item_tx = ItemTransactionModel.objects.get(bill_model=bill_model)

        self.assertEqual(item_tx.bill_model_id, bill_model.uuid)
        self.assertIsNone(item_tx.invoice_model_id)
        self.assertIsNone(item_tx.ce_model_id)
        self.assertIsNone(item_tx.po_model_id)
        self.assertEqual(item_tx.item_model_id, setup["expense_item"].uuid)
        self.assertEqual(item_tx.quantity, Decimal("2.00"))
        self.assertEqual(item_tx.unit_cost, Decimal("50.00"))
        self.assertEqual(item_tx.total_amount, Decimal("100.00"))

    def test_invoice_item_transaction_belongs_only_to_invoice_document(self):
        setup = self.create_entity_with_document_setup()
        invoice_model = self.create_invoice(setup)

        self.migrate_invoice_item(invoice_model, setup)

        item_tx = ItemTransactionModel.objects.get(invoice_model=invoice_model)

        self.assertEqual(item_tx.invoice_model_id, invoice_model.uuid)
        self.assertIsNone(item_tx.bill_model_id)
        self.assertIsNone(item_tx.ce_model_id)
        self.assertIsNone(item_tx.po_model_id)
        self.assertEqual(item_tx.item_model_id, setup["service_item"].uuid)
        self.assertEqual(item_tx.quantity, Decimal("2.00"))
        self.assertEqual(item_tx.unit_cost, Decimal("75.00"))
        self.assertEqual(item_tx.total_amount, Decimal("150.00"))

    def test_estimate_item_transaction_belongs_only_to_estimate_document(self):
        setup = self.create_entity_with_document_setup()
        estimate_model = self.create_estimate(setup)

        self.migrate_estimate_item(estimate_model, setup)

        item_tx = ItemTransactionModel.objects.get(ce_model=estimate_model)

        self.assertEqual(item_tx.ce_model_id, estimate_model.uuid)
        self.assertIsNone(item_tx.bill_model_id)
        self.assertIsNone(item_tx.invoice_model_id)
        self.assertIsNone(item_tx.po_model_id)
        self.assertEqual(item_tx.item_model_id, setup["service_item"].uuid)
        self.assertEqual(item_tx.ce_quantity, Decimal("2.00"))
        self.assertEqual(item_tx.ce_unit_cost_estimate, Decimal("30.00"))
        self.assertEqual(item_tx.ce_unit_revenue_estimate, Decimal("75.00"))
        self.assertEqual(item_tx.ce_cost_estimate, Decimal("60.00"))
        self.assertEqual(item_tx.ce_revenue_estimate, Decimal("150.00"))

    def test_purchase_order_item_transaction_belongs_only_to_purchase_order_document(self):
        setup = self.create_entity_with_document_setup()
        po_model = self.create_purchase_order(setup)

        self.migrate_purchase_order_item(po_model, setup)

        item_tx = ItemTransactionModel.objects.get(po_model=po_model)

        self.assertEqual(item_tx.po_model_id, po_model.uuid)
        self.assertIsNone(item_tx.bill_model_id)
        self.assertIsNone(item_tx.invoice_model_id)
        self.assertIsNone(item_tx.ce_model_id)
        self.assertEqual(item_tx.item_model_id, setup["inventory_item"].uuid)
        self.assertEqual(item_tx.po_quantity, Decimal("3.00"))
        self.assertEqual(item_tx.po_unit_cost, Decimal("20.00"))
        self.assertEqual(item_tx.po_total_amount, Decimal("60.00"))

    def test_item_transaction_owner_fields_are_mutually_exclusive_for_document_migrations(self):
        setup = self.create_entity_with_document_setup()

        bill_model = self.create_bill(setup)
        invoice_model = self.create_invoice(setup)
        estimate_model = self.create_estimate(setup)
        po_model = self.create_purchase_order(setup)

        self.migrate_bill_item(bill_model, setup)
        self.migrate_invoice_item(invoice_model, setup)
        self.migrate_estimate_item(estimate_model, setup)
        self.migrate_purchase_order_item(po_model, setup)

        for item_tx in ItemTransactionModel.objects.all():
            owner_count = sum(
                [
                    item_tx.bill_model_id is not None,
                    item_tx.invoice_model_id is not None,
                    item_tx.ce_model_id is not None,
                    item_tx.po_model_id is not None,
                ]
            )

            self.assertEqual(
                owner_count,
                1,
                "Each migrated ItemTransactionModel should belong to exactly one document owner.",
            )

    def test_document_amounts_are_updated_from_item_transaction_totals(self):
        setup = self.create_entity_with_document_setup()

        bill_model = self.create_bill(setup)
        invoice_model = self.create_invoice(setup)
        estimate_model = self.create_estimate(setup)
        po_model = self.create_purchase_order(setup)

        bill_model = self.migrate_bill_item(bill_model, setup)
        invoice_model = self.migrate_invoice_item(invoice_model, setup)
        estimate_model = self.migrate_estimate_item(estimate_model, setup)
        po_model = self.migrate_purchase_order_item(po_model, setup)

        self.assertEqual(bill_model.amount_due, Decimal("100.00"))
        self.assertEqual(invoice_model.amount_due, Decimal("150.00"))
        self.assertEqual(estimate_model.revenue_estimate, Decimal("150.00"))
        self.assertEqual(estimate_model.labor_estimate, Decimal("60.00"))
        self.assertEqual(po_model.po_amount, Decimal("60.00"))
