"""
High-level API tests for ItemTransactionModel amount and status helpers.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_INVENTORY,
    ASSET_CA_PREPAID,
    ASSET_CA_RECEIVABLES,
    COGS,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
    LIABILITY_CL_DEFERRED_REVENUE,
)
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


class ItemTransactionAmountStatusAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_itemtx_amount_status_admin",
            email="api-itemtx-amount-status-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API ItemTx Amount Status Entity"):
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
        prepaid_account = coa_model.create_account(
            code="1310",
            name=f"{name} Prepaid Account",
            role=ASSET_CA_PREPAID,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        inventory_account = coa_model.create_account(
            code="1510",
            name=f"{name} Inventory Account",
            role=ASSET_CA_INVENTORY,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        accounts_payable = coa_model.create_account(
            code="2010",
            name=f"{name} Accounts Payable",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        unearned_account = coa_model.create_account(
            code="2310",
            name=f"{name} Deferred Revenue",
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
            unit_abbr=f"ia-{str(entity_model.uuid)[:6]}",
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
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
            "receivable_account": receivable_account,
            "prepaid_account": prepaid_account,
            "accounts_payable": accounts_payable,
            "unearned_account": unearned_account,
            "customer_model": customer_model,
            "vendor_model": vendor_model,
            "service_item": service_item,
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
            user_model=self.admin_user,
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
            user_model=self.admin_user,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        return invoice_model

    def create_estimate(self, setup):
        estimate_model = EstimateModel(terms=EstimateModel.CONTRACT_TERMS_FIXED)
        estimate_model.configure(
            entity_slug=setup["entity_model"],
            customer_model=setup["customer_model"],
            user_model=self.admin_user,
            date_draft=date(2026, 1, 15),
            estimate_title="API ItemTx Amount Status Estimate",
            commit=True,
        )
        return estimate_model

    def create_purchase_order(self, setup):
        po_model = PurchaseOrderModel()
        po_model.configure(
            entity_slug=setup["entity_model"],
            po_title="API ItemTx Amount Status Purchase Order",
            user_model=self.admin_user,
            draft_date=date(2026, 1, 15),
            commit=True,
        )
        return po_model

    def make_item_transaction(self, **kwargs):
        item_tx = ItemTransactionModel(**kwargs)
        item_tx.clean()
        return item_tx

    def test_bill_and_invoice_total_amount_helpers_compute_quantity_times_unit_cost(self):
        setup = self.create_entity_setup()
        bill_item_tx = self.make_item_transaction(
            item_model=setup["expense_item"],
            bill_model=self.create_bill(setup),
            quantity=2.0,
            unit_cost=50.0,
        )
        invoice_item_tx = self.make_item_transaction(
            item_model=setup["service_item"],
            invoice_model=self.create_invoice(setup),
            quantity=3.0,
            unit_cost=75.0,
        )

        self.assertEqual(bill_item_tx.total_amount, Decimal("100.00"))
        self.assertEqual(invoice_item_tx.total_amount, Decimal("225.00"))

    def test_purchase_order_total_helper_computes_authorized_amount(self):
        setup = self.create_entity_setup()
        po_item_tx = self.make_item_transaction(
            item_model=setup["inventory_item"],
            po_model=self.create_purchase_order(setup),
            po_quantity=4.0,
            po_unit_cost=20.0,
            po_item_status=ItemTransactionModel.STATUS_ORDERED,
        )

        self.assertEqual(po_item_tx.po_total_amount, Decimal("80.00"))

    def test_estimate_cost_and_revenue_helpers_compute_current_totals(self):
        setup = self.create_entity_setup()
        estimate_item_tx = self.make_item_transaction(
            item_model=setup["service_item"],
            ce_model=self.create_estimate(setup),
            ce_quantity=2.0,
            ce_unit_cost_estimate=30.0,
            ce_unit_revenue_estimate=75.0,
        )

        self.assertEqual(estimate_item_tx.ce_cost_estimate, Decimal("60.00"))
        self.assertEqual(estimate_item_tx.ce_revenue_estimate, Decimal("150"))

    def test_po_backed_bill_line_cannot_exceed_authorized_quantity_or_amount(self):
        setup = self.create_entity_setup()
        bill_model = self.create_bill(setup)
        po_model = self.create_purchase_order(setup)

        quantity_too_high = ItemTransactionModel(
            item_model=setup["inventory_item"],
            bill_model=bill_model,
            po_model=po_model,
            po_quantity=4.0,
            po_unit_cost=20.0,
            quantity=5.0,
            unit_cost=20.0,
            po_item_status=ItemTransactionModel.STATUS_ORDERED,
        )
        amount_too_high = ItemTransactionModel(
            item_model=setup["inventory_item"],
            bill_model=bill_model,
            po_model=po_model,
            po_quantity=4.0,
            po_unit_cost=20.0,
            quantity=4.0,
            unit_cost=25.0,
            po_item_status=ItemTransactionModel.STATUS_ORDERED,
        )

        with self.assertRaises(ValidationError):
            quantity_too_high.clean()
        with self.assertRaises(ValidationError):
            amount_too_high.clean()

    def test_can_create_bill_reflects_bill_link_and_purchase_status(self):
        setup = self.create_entity_setup()
        po_model = self.create_purchase_order(setup)
        ordered_item_tx = self.make_item_transaction(
            item_model=setup["inventory_item"],
            po_model=po_model,
            po_quantity=4.0,
            po_unit_cost=20.0,
            po_item_status=ItemTransactionModel.STATUS_ORDERED,
        )
        not_ordered_item_tx = self.make_item_transaction(
            item_model=setup["inventory_item"],
            po_model=po_model,
            po_quantity=4.0,
            po_unit_cost=20.0,
            po_item_status=ItemTransactionModel.STATUS_NOT_ORDERED,
        )
        already_billed_item_tx = self.make_item_transaction(
            item_model=setup["inventory_item"],
            bill_model=self.create_bill(setup),
            po_model=po_model,
            po_quantity=4.0,
            po_unit_cost=20.0,
            quantity=1.0,
            unit_cost=20.0,
            po_item_status=ItemTransactionModel.STATUS_RECEIVED,
        )

        self.assertTrue(ordered_item_tx.can_create_bill())
        self.assertFalse(not_ordered_item_tx.can_create_bill())
        self.assertFalse(already_billed_item_tx.can_create_bill())

    def test_instance_status_helpers_reflect_purchase_order_status(self):
        ordered_item_tx = ItemTransactionModel(po_item_status=ItemTransactionModel.STATUS_ORDERED)
        received_item_tx = ItemTransactionModel(po_item_status=ItemTransactionModel.STATUS_RECEIVED)
        canceled_item_tx = ItemTransactionModel(po_item_status=ItemTransactionModel.STATUS_CANCELED)

        self.assertTrue(ordered_item_tx.is_ordered())
        self.assertFalse(received_item_tx.is_ordered())
        self.assertTrue(received_item_tx.is_received())
        self.assertTrue(canceled_item_tx.is_canceled())

    def test_status_css_helper_reflects_current_purchase_order_status(self):
        ordered_item_tx = ItemTransactionModel(po_item_status=ItemTransactionModel.STATUS_ORDERED)
        in_transit_item_tx = ItemTransactionModel(po_item_status=ItemTransactionModel.STATUS_IN_TRANSIT)
        received_item_tx = ItemTransactionModel(po_item_status=ItemTransactionModel.STATUS_RECEIVED)
        canceled_item_tx = ItemTransactionModel(po_item_status=ItemTransactionModel.STATUS_CANCELED)

        self.assertEqual(ordered_item_tx.get_status_css_class(), " is-info")
        self.assertEqual(in_transit_item_tx.get_status_css_class(), " is-warning")
        self.assertEqual(received_item_tx.get_status_css_class(), " is-success")
        self.assertEqual(canceled_item_tx.get_status_css_class(), " is-danger")

    def test_document_ownership_helpers_identify_associated_document(self):
        setup = self.create_entity_setup()
        bill_item_tx = self.make_item_transaction(
            item_model=setup["expense_item"],
            bill_model=self.create_bill(setup),
            quantity=1.0,
            unit_cost=10.0,
        )
        invoice_item_tx = self.make_item_transaction(
            item_model=setup["service_item"],
            invoice_model=self.create_invoice(setup),
            quantity=1.0,
            unit_cost=10.0,
        )
        estimate_item_tx = self.make_item_transaction(
            item_model=setup["service_item"],
            ce_model=self.create_estimate(setup),
            ce_quantity=1.0,
            ce_unit_cost_estimate=10.0,
            ce_unit_revenue_estimate=20.0,
        )
        po_item_tx = self.make_item_transaction(
            item_model=setup["inventory_item"],
            po_model=self.create_purchase_order(setup),
            po_quantity=1.0,
            po_unit_cost=10.0,
        )

        self.assertTrue(bill_item_tx.has_bill())
        self.assertTrue(invoice_item_tx.has_invoice())
        self.assertTrue(estimate_item_tx.has_estimate())
        self.assertTrue(po_item_tx.has_po())

    def test_html_id_and_string_helpers_return_stable_user_facing_context(self):
        setup = self.create_entity_setup()
        bill_item_tx = self.make_item_transaction(
            item_model=setup["expense_item"],
            bill_model=self.create_bill(setup),
            quantity=2.0,
            unit_cost=50.0,
        )

        self.assertIn(str(bill_item_tx.uuid), bill_item_tx.html_id())
        self.assertIn(str(bill_item_tx.uuid), bill_item_tx.html_id_unit_cost())
        self.assertIn(str(bill_item_tx.uuid), bill_item_tx.html_id_quantity())

        display = str(bill_item_tx)
        self.assertTrue(display)
        self.assertIn("Bill Model", display)
        self.assertIn("100.00", display)
