"""
High-level API behavior tests for EntityStateModel numbering state contracts.

These tests document deterministic, user-visible numbering behavior and the
state scoping that backs it.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import (
    BillModel,
    EstimateModel,
    InvoiceModel,
    JournalEntryModel,
    LedgerModel,
    PurchaseOrderModel,
)
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel, EntityStateModel
from django_ledger.models.items import ItemModel
from django_ledger.models.vendor import VendorModel
from django_ledger.settings import DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING


class EntityStateHighLevelAPITest(TestCase):
    """
    High-level behavior tests for EntityStateModel sequence contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic state/sequence invariants that should
    remain true across swappable-model refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_entity_state_contract_user",
            email="api-entity-state-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_setup(self, *, name="API Entity State Contract Entity", fy_start_month=1):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=fy_start_month,
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
            unit_abbr="state",
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
        }

    def create_customer(self, setup, *, suffix):
        customer_model = CustomerModel(
            customer_name=f"API Entity State Customer {suffix}",
            entity_model=setup["entity_model"],
            description=f"API Entity State Customer {suffix} description",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        return customer_model

    def create_vendor(self, setup, *, suffix):
        vendor_model = VendorModel(
            vendor_name=f"API Entity State Vendor {suffix}",
            entity_model=setup["entity_model"],
            description=f"API Entity State Vendor {suffix} description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()
        return vendor_model

    def create_service_item(self, setup, *, suffix):
        return setup["entity_model"].create_item_service(
            name=f"API Entity State Service Item {suffix}",
            uom_model=setup["uom_model"],
            coa_model=setup["coa_model"],
            commit=True,
        )

    def create_bill(self, setup, *, date_draft=date(2026, 1, 15)):
        bill_model = BillModel(
            vendor=setup["vendor_model"],
            cash_account=setup["cash_account"],
            prepaid_account=setup["prepaid_account"],
            unearned_account=setup["accounts_payable"],
        )

        _ledger_model, bill_model = bill_model.configure(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            date_draft=date_draft,
            commit=True,
        )

        return bill_model

    def create_invoice(self, setup, *, date_draft=date(2026, 1, 15)):
        invoice_model = InvoiceModel(
            customer=setup["customer_model"],
            cash_account=setup["cash_account"],
            prepaid_account=setup["receivable_account"],
            unearned_account=setup["unearned_account"],
        )

        _ledger_model, invoice_model = invoice_model.configure(
            entity_slug=setup["entity_model"],
            user_model=self.user,
            date_draft=date_draft,
            commit=True,
        )

        return invoice_model

    def create_estimate(self, setup, *, date_draft=date(2026, 1, 15)):
        estimate_model = EstimateModel(
            terms=EstimateModel.CONTRACT_TERMS_FIXED,
        )

        estimate_model.configure(
            entity_slug=setup["entity_model"],
            customer_model=setup["customer_model"],
            user_model=self.user,
            date_draft=date_draft,
            estimate_title="API Entity State Estimate",
            commit=True,
        )

        return estimate_model

    def create_purchase_order(self, setup, *, draft_date=date(2026, 1, 15)):
        po_model = PurchaseOrderModel()

        po_model.configure(
            entity_slug=setup["entity_model"],
            po_title="API Entity State Purchase Order",
            user_model=self.user,
            draft_date=draft_date,
            commit=True,
        )

        return po_model

    def create_journal_entry(self, setup, *, timestamp=None):
        ledger_model, _created = LedgerModel.objects.get_or_create(
            entity=setup["entity_model"],
            ledger_xid="api-entity-state-ledger",
            defaults={
                "name": "API Entity State Ledger",
            },
        )

        journal_entry = JournalEntryModel.objects.create(
            ledger=ledger_model,
            timestamp=timestamp if timestamp is not None else self.make_timestamp(),
            description="API Entity State Journal Entry",
        )

        journal_entry.generate_je_number(commit=True)
        journal_entry.refresh_from_db()

        return journal_entry

    def get_state(self, setup, *, key, fiscal_year=None, entity_unit=None):
        return EntityStateModel.objects.get(
            entity_model=setup["entity_model"],
            entity_unit=entity_unit,
            fiscal_year=fiscal_year,
            key=key,
        )

    def assert_number_ends_with_sequence(self, number, sequence):
        self.assertTrue(number)
        self.assertTrue(number.endswith(str(sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)))

    def test_customer_vendor_and_item_states_are_entity_scoped_without_fiscal_year(self):
        setup = self.create_entity_setup()

        customer_a = self.create_customer(setup, suffix="A")
        customer_b = self.create_customer(setup, suffix="B")
        vendor_a = self.create_vendor(setup, suffix="A")
        vendor_b = self.create_vendor(setup, suffix="B")
        service_item_a = self.create_service_item(setup, suffix="A")
        service_item_b = self.create_service_item(setup, suffix="B")

        self.assertNotEqual(customer_a.customer_number, customer_b.customer_number)
        self.assert_number_ends_with_sequence(customer_a.customer_number, 2)
        self.assert_number_ends_with_sequence(customer_b.customer_number, 3)

        self.assertNotEqual(vendor_a.vendor_number, vendor_b.vendor_number)
        self.assert_number_ends_with_sequence(vendor_a.vendor_number, 2)
        self.assert_number_ends_with_sequence(vendor_b.vendor_number, 3)

        self.assertNotEqual(service_item_a.item_number, service_item_b.item_number)
        self.assert_number_ends_with_sequence(service_item_a.item_number, 3)
        self.assert_number_ends_with_sequence(service_item_b.item_number, 4)

        customer_state = self.get_state(
            setup,
            key=EntityStateModel.KEY_CUSTOMER,
            fiscal_year=None,
        )
        vendor_state = self.get_state(
            setup,
            key=EntityStateModel.KEY_VENDOR,
            fiscal_year=None,
        )
        item_state = self.get_state(
            setup,
            key=EntityStateModel.KEY_ITEM,
            fiscal_year=None,
        )

        # setup already creates one customer, one vendor and one service item.
        self.assertEqual(customer_state.sequence, 3)
        self.assertEqual(vendor_state.sequence, 3)

        # setup creates service + expense items, then this test creates 2 more.
        self.assertEqual(item_state.sequence, 4)

        self.assertIsNone(customer_state.entity_unit_id)
        self.assertIsNone(customer_state.fiscal_year)
        self.assertIsNone(vendor_state.entity_unit_id)
        self.assertIsNone(vendor_state.fiscal_year)
        self.assertIsNone(item_state.entity_unit_id)
        self.assertIsNone(item_state.fiscal_year)

    def test_document_numbers_advance_by_document_type_and_fiscal_year(self):
        setup = self.create_entity_setup()
        fy_key = setup["entity_model"].get_fy_for_date(dt=date(2026, 1, 15))

        bill_a = self.create_bill(setup)
        bill_b = self.create_bill(setup)

        invoice_a = self.create_invoice(setup)
        invoice_b = self.create_invoice(setup)

        estimate_a = self.create_estimate(setup)
        estimate_b = self.create_estimate(setup)

        po_a = self.create_purchase_order(setup)
        po_b = self.create_purchase_order(setup)

        self.assertNotEqual(bill_a.bill_number, bill_b.bill_number)
        self.assertIn(f"-{fy_key}-", bill_a.bill_number)
        self.assertIn(f"-{fy_key}-", bill_b.bill_number)
        self.assert_number_ends_with_sequence(bill_a.bill_number, 1)
        self.assert_number_ends_with_sequence(bill_b.bill_number, 2)

        self.assertNotEqual(invoice_a.invoice_number, invoice_b.invoice_number)
        self.assertIn(f"-{fy_key}-", invoice_a.invoice_number)
        self.assertIn(f"-{fy_key}-", invoice_b.invoice_number)
        self.assert_number_ends_with_sequence(invoice_a.invoice_number, 1)
        self.assert_number_ends_with_sequence(invoice_b.invoice_number, 2)

        self.assertNotEqual(estimate_a.estimate_number, estimate_b.estimate_number)
        self.assertIn(f"-{fy_key}-", estimate_a.estimate_number)
        self.assertIn(f"-{fy_key}-", estimate_b.estimate_number)
        self.assert_number_ends_with_sequence(estimate_a.estimate_number, 1)
        self.assert_number_ends_with_sequence(estimate_b.estimate_number, 2)

        self.assertNotEqual(po_a.po_number, po_b.po_number)
        self.assertIn(f"-{fy_key}-", po_a.po_number)
        self.assertIn(f"-{fy_key}-", po_b.po_number)
        self.assert_number_ends_with_sequence(po_a.po_number, 1)
        self.assert_number_ends_with_sequence(po_b.po_number, 2)

        bill_state = self.get_state(
            setup,
            key=EntityStateModel.KEY_BILL,
            fiscal_year=fy_key,
        )
        invoice_state = self.get_state(
            setup,
            key=EntityStateModel.KEY_INVOICE,
            fiscal_year=fy_key,
        )
        estimate_state = self.get_state(
            setup,
            key=EntityStateModel.KEY_ESTIMATE,
            fiscal_year=fy_key,
        )
        po_state = self.get_state(
            setup,
            key=EntityStateModel.KEY_PURCHASE_ORDER,
            fiscal_year=fy_key,
        )

        self.assertEqual(bill_state.sequence, 2)
        self.assertEqual(invoice_state.sequence, 2)
        self.assertEqual(estimate_state.sequence, 2)
        self.assertEqual(po_state.sequence, 2)

        self.assertIsNone(bill_state.entity_unit_id)
        self.assertIsNone(invoice_state.entity_unit_id)
        self.assertIsNone(estimate_state.entity_unit_id)
        self.assertIsNone(po_state.entity_unit_id)

    def test_document_numbers_start_independently_per_entity(self):
        setup_a = self.create_entity_setup(name="API Entity State A")
        setup_b = self.create_entity_setup(name="API Entity State B")

        fy_a = setup_a["entity_model"].get_fy_for_date(dt=date(2026, 1, 15))
        fy_b = setup_b["entity_model"].get_fy_for_date(dt=date(2026, 1, 15))

        bill_a = self.create_bill(setup_a)
        bill_b = self.create_bill(setup_b)

        self.assertIn(f"-{fy_a}-", bill_a.bill_number)
        self.assertIn(f"-{fy_b}-", bill_b.bill_number)
        self.assert_number_ends_with_sequence(bill_a.bill_number, 1)
        self.assert_number_ends_with_sequence(bill_b.bill_number, 1)

        bill_state_a = self.get_state(
            setup_a,
            key=EntityStateModel.KEY_BILL,
            fiscal_year=fy_a,
        )
        bill_state_b = self.get_state(
            setup_b,
            key=EntityStateModel.KEY_BILL,
            fiscal_year=fy_b,
        )

        self.assertEqual(bill_state_a.sequence, 1)
        self.assertEqual(bill_state_b.sequence, 1)
        self.assertNotEqual(bill_state_a.entity_model_id, bill_state_b.entity_model_id)

    def test_document_numbering_resets_across_non_calendar_fiscal_year(self):
        setup = self.create_entity_setup(fy_start_month=4)

        march_bill = self.create_bill(setup, date_draft=date(2026, 3, 31))
        april_bill_a = self.create_bill(setup, date_draft=date(2026, 4, 1))
        april_bill_b = self.create_bill(setup, date_draft=date(2026, 4, 2))

        march_fy = setup["entity_model"].get_fy_for_date(dt=date(2026, 3, 31))
        april_fy = setup["entity_model"].get_fy_for_date(dt=date(2026, 4, 1))

        self.assertEqual(march_fy, 2025)
        self.assertEqual(april_fy, 2026)

        self.assertIn(f"-{march_fy}-", march_bill.bill_number)
        self.assert_number_ends_with_sequence(march_bill.bill_number, 1)

        self.assertIn(f"-{april_fy}-", april_bill_a.bill_number)
        self.assertIn(f"-{april_fy}-", april_bill_b.bill_number)
        self.assertNotEqual(april_bill_a.bill_number, april_bill_b.bill_number)
        self.assert_number_ends_with_sequence(april_bill_a.bill_number, 1)
        self.assert_number_ends_with_sequence(april_bill_b.bill_number, 2)

        march_state = self.get_state(
            setup,
            key=EntityStateModel.KEY_BILL,
            fiscal_year=march_fy,
        )
        april_state = self.get_state(
            setup,
            key=EntityStateModel.KEY_BILL,
            fiscal_year=april_fy,
        )

        bill_state_count = EntityStateModel.objects.filter(
            entity_model=setup["entity_model"],
            entity_unit=None,
            key=EntityStateModel.KEY_BILL,
        ).count()

        self.assertEqual(bill_state_count, 2)
        self.assertEqual(march_state.sequence, 1)
        self.assertEqual(april_state.sequence, 2)

    def test_journal_entry_numbers_advance_by_fiscal_year_without_entity_unit(self):
        setup = self.create_entity_setup()
        fy_key = setup["entity_model"].get_fy_for_date(dt=self.make_timestamp())

        journal_entry_a = self.create_journal_entry(setup)
        journal_entry_b = self.create_journal_entry(setup)

        self.assertNotEqual(journal_entry_a.je_number, journal_entry_b.je_number)
        self.assertIn(f"-{fy_key}-", journal_entry_a.je_number)
        self.assertIn(f"-{fy_key}-", journal_entry_b.je_number)
        self.assert_number_ends_with_sequence(journal_entry_a.je_number, 1)
        self.assert_number_ends_with_sequence(journal_entry_b.je_number, 2)

        je_state = self.get_state(
            setup,
            key=EntityStateModel.KEY_JOURNAL_ENTRY,
            fiscal_year=fy_key,
        )

        self.assertEqual(je_state.sequence, 2)
        self.assertIsNone(je_state.entity_unit_id)
