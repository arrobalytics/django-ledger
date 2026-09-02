"""
High-level API behavior tests for ReceiptModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import ReceiptModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel, EntityStateModel
from django_ledger.models.receipt import ReceiptModelValidationError
from django_ledger.models.unit import EntityUnitModel
from django_ledger.models.vendor import VendorModel


class ReceiptHighLevelAPITest(TestCase):
    """
    High-level behavior tests for ReceiptModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic receipt invariants that should remain
    true across swappable-model refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_receipt_contract_user",
            email="api-receipt-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Receipt Contract Entity"):
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

        income_account = coa_model.create_account(
            code="4010",
            name=f"{name} Income Account",
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

        transfer_account = coa_model.create_account(
            code="1020",
            name=f"{name} Transfer Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
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

        unit_model = EntityUnitModel.add_root(
            name=f"{name} Unit",
            slug="api-receipt-unit",
            entity=entity_model,
            document_prefix="RCU",
            active=True,
            hidden=False,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
            "income_account": income_account,
            "expense_account": expense_account,
            "transfer_account": transfer_account,
            "customer_model": customer_model,
            "vendor_model": vendor_model,
            "unit_model": unit_model,
        }

    def create_sales_receipt(self, setup, *, receipt_date=date(2026, 1, 15), amount="125.00"):
        receipt_model = ReceiptModel()

        receipt_model.configure(
            entity_model=setup["entity_model"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            amount=Decimal(amount),
            receipt_date=receipt_date,
            customer_model=setup["customer_model"],
            charge_account=setup["cash_account"],
            receipt_account=setup["income_account"],
            commit=True,
        )

        receipt_model.refresh_from_db()
        return receipt_model

    def create_expense_receipt(self, setup, *, receipt_date=date(2026, 1, 15), amount="75.00"):
        receipt_model = ReceiptModel()

        receipt_model.configure(
            entity_model=setup["entity_model"],
            receipt_type=ReceiptModel.EXPENSE_RECEIPT,
            amount=Decimal(amount),
            receipt_date=receipt_date,
            vendor_model=setup["vendor_model"],
            charge_account=setup["cash_account"],
            receipt_account=setup["expense_account"],
            commit=True,
        )

        receipt_model.refresh_from_db()
        return receipt_model

    def create_transfer_receipt(self, setup, *, receipt_date=date(2026, 1, 15), amount="50.00"):
        receipt_model = ReceiptModel()

        receipt_model.configure(
            entity_model=setup["entity_model"],
            receipt_type=ReceiptModel.TRANSFER_RECEIPT,
            amount=Decimal(amount),
            receipt_date=receipt_date,
            charge_account=setup["cash_account"],
            receipt_account=setup["transfer_account"],
            commit=True,
        )

        receipt_model.refresh_from_db()
        return receipt_model

    def test_sales_receipt_configure_creates_customer_receipt_and_posted_ledger(self):
        setup = self.create_entity_setup()

        receipt_model = self.create_sales_receipt(setup)

        self.assertIsInstance(receipt_model, ReceiptModel)
        self.assertIsNotNone(receipt_model.uuid)
        self.assertTrue(receipt_model.receipt_number)
        self.assertEqual(receipt_model.receipt_type, ReceiptModel.SALES_RECEIPT)
        self.assertEqual(receipt_model.amount, Decimal("125.00"))
        self.assertEqual(receipt_model.customer_model_id, setup["customer_model"].uuid)
        self.assertIsNone(receipt_model.vendor_model_id)
        self.assertEqual(receipt_model.charge_account_id, setup["cash_account"].uuid)
        self.assertEqual(receipt_model.receipt_account_id, setup["income_account"].uuid)
        self.assertTrue(receipt_model.is_sales_receipt())
        self.assertFalse(receipt_model.is_expense_receipt())
        self.assertFalse(receipt_model.is_transfer_receipt())
        self.assertTrue(receipt_model.is_configured())
        self.assertTrue(receipt_model.can_migrate())

        self.assertIsNotNone(receipt_model.ledger_model_id)
        self.assertEqual(receipt_model.ledger_model.entity_id, setup["entity_model"].uuid)
        self.assertTrue(receipt_model.ledger_model.is_posted())
        self.assertEqual(receipt_model.ledger_model.name, receipt_model.receipt_number)

    def test_expense_receipt_configure_creates_vendor_receipt(self):
        setup = self.create_entity_setup()

        receipt_model = self.create_expense_receipt(setup)

        self.assertTrue(receipt_model.receipt_number)
        self.assertEqual(receipt_model.receipt_type, ReceiptModel.EXPENSE_RECEIPT)
        self.assertEqual(receipt_model.amount, Decimal("75.00"))
        self.assertEqual(receipt_model.vendor_model_id, setup["vendor_model"].uuid)
        self.assertIsNone(receipt_model.customer_model_id)
        self.assertEqual(receipt_model.charge_account_id, setup["cash_account"].uuid)
        self.assertEqual(receipt_model.receipt_account_id, setup["expense_account"].uuid)
        self.assertTrue(receipt_model.is_expense_receipt())
        self.assertFalse(receipt_model.is_sales_receipt())
        self.assertFalse(receipt_model.is_transfer_receipt())
        self.assertTrue(receipt_model.is_configured())
        self.assertTrue(receipt_model.can_migrate())

    def test_transfer_receipt_configure_does_not_require_customer_or_vendor(self):
        setup = self.create_entity_setup()

        receipt_model = self.create_transfer_receipt(setup)

        self.assertTrue(receipt_model.receipt_number)
        self.assertEqual(receipt_model.receipt_type, ReceiptModel.TRANSFER_RECEIPT)
        self.assertIsNone(receipt_model.customer_model_id)
        self.assertIsNone(receipt_model.vendor_model_id)
        self.assertTrue(receipt_model.is_transfer_receipt())
        self.assertFalse(receipt_model.is_sales_receipt())
        self.assertFalse(receipt_model.is_expense_receipt())
        self.assertTrue(receipt_model.is_configured())
        self.assertTrue(receipt_model.can_migrate())

    def test_receipt_for_entity_limits_queryset_to_entity_scope(self):
        setup = self.create_entity_setup(name="API Receipt Entity A")
        other_setup = self.create_entity_setup(name="API Receipt Entity B")

        receipt_model = self.create_sales_receipt(setup)
        other_receipt_model = self.create_sales_receipt(other_setup)

        scoped_qs = ReceiptModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(scoped_qs.filter(uuid=receipt_model.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_receipt_model.uuid).exists())

    def test_receipt_queryset_customer_vendor_and_date_filters(self):
        setup = self.create_entity_setup()

        sales_receipt = self.create_sales_receipt(
            setup,
            receipt_date=date(2026, 1, 15),
        )

        expense_receipt = self.create_expense_receipt(
            setup,
            receipt_date=date(2026, 2, 20),
        )

        receipts_qs = ReceiptModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(
            receipts_qs.for_customer(setup["customer_model"]).filter(uuid=sales_receipt.uuid).exists()
        )
        self.assertFalse(
            receipts_qs.for_customer(setup["customer_model"]).filter(uuid=expense_receipt.uuid).exists()
        )

        self.assertTrue(
            receipts_qs.for_vendor(setup["vendor_model"]).filter(uuid=expense_receipt.uuid).exists()
        )
        self.assertFalse(
            receipts_qs.for_vendor(setup["vendor_model"]).filter(uuid=sales_receipt.uuid).exists()
        )

        january_qs = receipts_qs.for_dates(
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        self.assertTrue(january_qs.filter(uuid=sales_receipt.uuid).exists())
        self.assertFalse(january_qs.filter(uuid=expense_receipt.uuid).exists())

    def test_receipt_numbering_uses_entity_state_receipt_key_and_fiscal_year(self):
        setup = self.create_entity_setup()

        self.create_sales_receipt(setup)
        self.create_expense_receipt(setup)

        fy_key = setup["entity_model"].get_fy_for_date(dt=date(2026, 1, 15))

        receipt_state = EntityStateModel.objects.get(
            entity_model=setup["entity_model"],
            entity_unit=None,
            fiscal_year=fy_key,
            key=EntityStateModel.KEY_RECEIPT,
        )

        self.assertEqual(receipt_state.sequence, 2)

    def test_receipt_numbering_is_entity_scoped(self):
        setup_a = self.create_entity_setup(name="API Receipt State Entity A")
        setup_b = self.create_entity_setup(name="API Receipt State Entity B")

        receipt_a = self.create_sales_receipt(setup_a)
        receipt_b = self.create_sales_receipt(setup_b)

        self.assertEqual(receipt_a.receipt_number, receipt_b.receipt_number)

        fy_a = setup_a["entity_model"].get_fy_for_date(dt=date(2026, 1, 15))
        fy_b = setup_b["entity_model"].get_fy_for_date(dt=date(2026, 1, 15))

        state_a = EntityStateModel.objects.get(
            entity_model=setup_a["entity_model"],
            entity_unit=None,
            fiscal_year=fy_a,
            key=EntityStateModel.KEY_RECEIPT,
        )
        state_b = EntityStateModel.objects.get(
            entity_model=setup_b["entity_model"],
            entity_unit=None,
            fiscal_year=fy_b,
            key=EntityStateModel.KEY_RECEIPT,
        )

        self.assertEqual(state_a.sequence, 1)
        self.assertEqual(state_b.sequence, 1)

    def test_receipt_configure_rejects_negative_amount(self):
        setup = self.create_entity_setup()

        receipt_model = ReceiptModel()

        with self.assertRaises(ReceiptModelValidationError):
            receipt_model.configure(
                entity_model=setup["entity_model"],
                receipt_type=ReceiptModel.SALES_RECEIPT,
                amount=Decimal("-1.00"),
                receipt_date=date(2026, 1, 15),
                customer_model=setup["customer_model"],
                charge_account=setup["cash_account"],
                receipt_account=setup["income_account"],
                commit=True,
            )

    def test_sales_receipt_requires_customer(self):
        setup = self.create_entity_setup()

        receipt_model = ReceiptModel()

        with self.assertRaises(ReceiptModelValidationError):
            receipt_model.configure(
                entity_model=setup["entity_model"],
                receipt_type=ReceiptModel.SALES_RECEIPT,
                amount=Decimal("10.00"),
                receipt_date=date(2026, 1, 15),
                charge_account=setup["cash_account"],
                receipt_account=setup["income_account"],
                commit=True,
            )

    def test_expense_receipt_requires_vendor(self):
        setup = self.create_entity_setup()

        receipt_model = ReceiptModel()

        with self.assertRaises(ReceiptModelValidationError):
            receipt_model.configure(
                entity_model=setup["entity_model"],
                receipt_type=ReceiptModel.EXPENSE_RECEIPT,
                amount=Decimal("10.00"),
                receipt_date=date(2026, 1, 15),
                charge_account=setup["cash_account"],
                receipt_account=setup["expense_account"],
                commit=True,
            )

    def test_transfer_receipt_rejects_customer_or_vendor(self):
        setup = self.create_entity_setup()

        receipt_model = ReceiptModel()

        with self.assertRaises(ReceiptModelValidationError):
            receipt_model.configure(
                entity_model=setup["entity_model"],
                receipt_type=ReceiptModel.TRANSFER_RECEIPT,
                amount=Decimal("10.00"),
                receipt_date=date(2026, 1, 15),
                customer_model=setup["customer_model"],
                charge_account=setup["cash_account"],
                receipt_account=setup["transfer_account"],
                commit=True,
            )

    def test_receipt_get_type_for_amount_contracts(self):
        setup = self.create_entity_setup()

        customer_receipt = ReceiptModel(customer_model=setup["customer_model"])
        vendor_receipt = ReceiptModel(vendor_model=setup["vendor_model"])

        self.assertEqual(
            customer_receipt.get_receipt_type_for_amount(Decimal("10.00")),
            ReceiptModel.SALES_RECEIPT,
        )
        self.assertEqual(
            customer_receipt.get_receipt_type_for_amount(Decimal("-10.00")),
            ReceiptModel.SALES_REFUND,
        )
        self.assertEqual(
            vendor_receipt.get_receipt_type_for_amount(Decimal("-10.00")),
            ReceiptModel.EXPENSE_RECEIPT,
        )
        self.assertEqual(
            vendor_receipt.get_receipt_type_for_amount(Decimal("10.00")),
            ReceiptModel.EXPENSE_REFUND,
        )

    def test_receipt_unit_model_can_be_bound_by_instance(self):
        setup = self.create_entity_setup()

        receipt_model = ReceiptModel()

        receipt_model.configure(
            entity_model=setup["entity_model"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            amount=Decimal("25.00"),
            unit_model=setup["unit_model"],
            receipt_date=date(2026, 1, 15),
            customer_model=setup["customer_model"],
            charge_account=setup["cash_account"],
            receipt_account=setup["income_account"],
            commit=True,
        )

        receipt_model.refresh_from_db()

        self.assertEqual(receipt_model.unit_model_id, setup["unit_model"].uuid)
