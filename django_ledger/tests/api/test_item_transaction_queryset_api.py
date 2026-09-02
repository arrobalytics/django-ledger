"""
High-level API tests for ItemTransactionModel manager and queryset behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
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
from django_ledger.models.items import ItemModel, ItemTransactionModelValidationError
from django_ledger.models.vendor import VendorModel


class ItemTransactionQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_itemtx_queryset_admin",
            email="api-itemtx-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_itemtx_queryset_manager",
            email="api-itemtx-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_itemtx_queryset_other_admin",
            email="api-itemtx-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_itemtx_queryset_unrelated",
            email="api-itemtx-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_itemtx_queryset_superuser",
            email="api-itemtx-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API ItemTx Queryset Entity", admin_user=None, manager_user=None):
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
        earnings_account = coa_model.create_account(
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
            unit_abbr=f"it-{str(entity_model.uuid)[:6]}",
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
            "earnings_account": earnings_account,
            "expense_account": expense_account,
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
            estimate_title="API ItemTx Queryset Estimate",
            commit=True,
        )
        return estimate_model

    def create_purchase_order(self, setup):
        po_model = PurchaseOrderModel()
        po_model.configure(
            entity_slug=setup["entity_model"],
            po_title="API ItemTx Queryset Purchase Order",
            user_model=self.admin_user,
            draft_date=date(2026, 1, 15),
            commit=True,
        )
        return po_model

    def create_item_transaction(self, **kwargs):
        item_tx = ItemTransactionModel(**kwargs)
        item_tx.clean()
        item_tx.save()
        return item_tx

    def create_bill_item_transaction(self, setup, bill_model):
        return self.create_item_transaction(
            item_model=setup["expense_item"],
            bill_model=bill_model,
            quantity=2.0,
            unit_cost=50.0,
        )

    def create_invoice_item_transaction(self, setup, invoice_model):
        return self.create_item_transaction(
            item_model=setup["service_item"],
            invoice_model=invoice_model,
            quantity=3.0,
            unit_cost=75.0,
        )

    def create_estimate_item_transaction(
        self,
        setup,
        estimate_model,
        *,
        quantity=2.0,
        unit_cost=30.0,
        unit_revenue=75.0,
    ):
        return self.create_item_transaction(
            item_model=setup["service_item"],
            ce_model=estimate_model,
            ce_quantity=quantity,
            ce_unit_cost_estimate=unit_cost,
            ce_unit_revenue_estimate=unit_revenue,
        )

    def create_po_item_transaction(self, setup, po_model, *, status=ItemTransactionModel.STATUS_ORDERED):
        return self.create_item_transaction(
            item_model=setup["inventory_item"],
            po_model=po_model,
            po_quantity=4.0,
            po_unit_cost=20.0,
            po_item_status=status,
        )

    def create_orphan_item_transaction(self, setup, *, status=None):
        return self.create_item_transaction(
            item_model=setup["inventory_item"],
            po_item_status=status,
        )

    def assert_itemtx_uuids(self, queryset, expected_item_txs):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {item_tx.uuid for item_tx in expected_item_txs},
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API ItemTx Entity A")
        other_setup = self.create_entity_setup(
            name="API ItemTx Entity B",
            admin_user=self.other_admin_user,
        )
        item_tx = self.create_orphan_item_transaction(setup)
        self.create_orphan_item_transaction(other_setup)

        self.assert_itemtx_uuids(ItemTransactionModel.objects.for_entity(setup["entity_model"]), [item_tx])
        self.assert_itemtx_uuids(ItemTransactionModel.objects.for_entity(setup["entity_model"].slug), [item_tx])
        self.assert_itemtx_uuids(ItemTransactionModel.objects.for_entity(setup["entity_model"].uuid), [item_tx])

    def test_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_orphan_item_transaction(self.create_entity_setup())

        with self.assertRaises(ItemTransactionModelValidationError):
            ItemTransactionModel.objects.for_entity(object())

        self.assertFalse(ItemTransactionModel.objects.for_entity("missing-itemtx-entity-slug").exists())

    def test_for_user_scopes_to_authorized_users_and_superuser(self):
        setup = self.create_entity_setup(
            name="API ItemTx Access Entity",
            manager_user=self.manager_user,
        )
        other_setup = self.create_entity_setup(
            name="API ItemTx Other Access Entity",
            admin_user=self.other_admin_user,
        )
        item_tx = self.create_orphan_item_transaction(setup)
        other_item_tx = self.create_orphan_item_transaction(other_setup)

        self.assert_itemtx_uuids(ItemTransactionModel.objects.all().for_user(self.admin_user), [item_tx])
        self.assert_itemtx_uuids(ItemTransactionModel.objects.all().for_user(self.manager_user), [item_tx])
        self.assertFalse(ItemTransactionModel.objects.all().for_user(self.unrelated_user).exists())
        self.assert_itemtx_uuids(
            ItemTransactionModel.objects.all().for_user(self.superuser),
            [item_tx, other_item_tx],
        )

    def test_document_relation_filters_return_only_matching_document_rows(self):
        setup = self.create_entity_setup()
        bill_model = self.create_bill(setup)
        invoice_model = self.create_invoice(setup)
        estimate_model = self.create_estimate(setup)
        po_model = self.create_purchase_order(setup)
        bill_item_tx = self.create_bill_item_transaction(setup, bill_model)
        invoice_item_tx = self.create_invoice_item_transaction(setup, invoice_model)
        estimate_item_tx = self.create_estimate_item_transaction(setup, estimate_model)
        po_item_tx = self.create_po_item_transaction(setup, po_model)

        self.assert_itemtx_uuids(
            ItemTransactionModel.objects.for_bill(bill_model.uuid, setup["entity_model"]),
            [bill_item_tx],
        )
        self.assert_itemtx_uuids(
            ItemTransactionModel.objects.for_invoice(invoice_model.uuid, setup["entity_model"]),
            [invoice_item_tx],
        )
        self.assert_itemtx_uuids(
            ItemTransactionModel.objects.for_estimate(estimate_model.uuid, setup["entity_model"]),
            [estimate_item_tx],
        )
        self.assert_itemtx_uuids(
            ItemTransactionModel.objects.for_po(po_model.uuid, setup["entity_model"]),
            [po_item_tx],
        )

    def test_for_contract_returns_direct_and_document_bound_estimate_rows(self):
        setup = self.create_entity_setup()
        estimate_model = self.create_estimate(setup)
        bill_model = self.create_bill(setup)
        invoice_model = self.create_invoice(setup)
        po_model = self.create_purchase_order(setup)

        bill_model.ce_model = estimate_model
        bill_model.save(update_fields=["ce_model", "updated"])
        invoice_model.ce_model = estimate_model
        invoice_model.save(update_fields=["ce_model", "updated"])
        po_model.ce_model = estimate_model
        po_model.save(update_fields=["ce_model", "updated"])

        estimate_item_tx = self.create_estimate_item_transaction(setup, estimate_model)
        bill_item_tx = self.create_bill_item_transaction(setup, bill_model)
        invoice_item_tx = self.create_invoice_item_transaction(setup, invoice_model)
        po_item_tx = self.create_po_item_transaction(setup, po_model)
        unrelated_bill_item_tx = self.create_bill_item_transaction(setup, self.create_bill(setup))

        contract_qs = ItemTransactionModel.objects.for_contract(estimate_model.uuid, setup["entity_model"])

        self.assert_itemtx_uuids(contract_qs, [estimate_item_tx, bill_item_tx, invoice_item_tx, po_item_tx])
        self.assertFalse(contract_qs.filter(uuid=unrelated_bill_item_tx.uuid).exists())

    def test_status_filters_return_matching_purchase_order_status_rows(self):
        setup = self.create_entity_setup()
        ordered_item_tx = self.create_orphan_item_transaction(
            setup,
            status=ItemTransactionModel.STATUS_ORDERED,
        )
        in_transit_item_tx = self.create_orphan_item_transaction(
            setup,
            status=ItemTransactionModel.STATUS_IN_TRANSIT,
        )
        received_item_tx = self.create_orphan_item_transaction(
            setup,
            status=ItemTransactionModel.STATUS_RECEIVED,
        )
        status_qs = ItemTransactionModel.objects.filter(
            uuid__in=[ordered_item_tx.uuid, in_transit_item_tx.uuid, received_item_tx.uuid],
        )

        self.assert_itemtx_uuids(status_qs.is_ordered(), [ordered_item_tx])
        self.assert_itemtx_uuids(status_qs.in_transit(), [in_transit_item_tx])
        self.assert_itemtx_uuids(status_qs.is_received(), [received_item_tx])

    def test_is_orphan_returns_only_rows_without_document_owner(self):
        setup = self.create_entity_setup()
        orphan_item_tx = self.create_orphan_item_transaction(setup)
        bill_item_tx = self.create_bill_item_transaction(setup, self.create_bill(setup))
        invoice_item_tx = self.create_invoice_item_transaction(setup, self.create_invoice(setup))
        po_item_tx = self.create_po_item_transaction(setup, self.create_purchase_order(setup))
        estimate_item_tx = self.create_estimate_item_transaction(setup, self.create_estimate(setup))
        item_tx_qs = ItemTransactionModel.objects.filter(
            uuid__in=[
                orphan_item_tx.uuid,
                bill_item_tx.uuid,
                invoice_item_tx.uuid,
                po_item_tx.uuid,
                estimate_item_tx.uuid,
            ],
        )

        self.assert_itemtx_uuids(item_tx_qs.is_orphan(), [orphan_item_tx])

    def test_get_estimate_aggregate_returns_cost_revenue_and_count_totals(self):
        setup = self.create_entity_setup()
        estimate_model = self.create_estimate(setup)
        first_item_tx = self.create_estimate_item_transaction(
            setup,
            estimate_model,
            quantity=2.0,
            unit_cost=30.0,
            unit_revenue=75.0,
        )
        second_item_tx = self.create_estimate_item_transaction(
            setup,
            estimate_model,
            quantity=1.0,
            unit_cost=20.0,
            unit_revenue=50.0,
        )

        aggregate = ItemTransactionModel.objects.filter(
            uuid__in=[first_item_tx.uuid, second_item_tx.uuid],
        ).get_estimate_aggregate()

        self.assertEqual(aggregate["total_items"], 2)
        self.assertEqual(aggregate["ce_cost_estimate__sum"], Decimal("80.00"))
        self.assertEqual(aggregate["ce_revenue_estimate__sum"], Decimal("200"))
