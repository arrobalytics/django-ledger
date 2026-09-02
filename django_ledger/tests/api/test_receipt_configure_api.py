"""
High-level API tests for ReceiptModel configuration and numbering behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.text import slugify

from django_ledger.models import ReceiptModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.receipt import ReceiptModelValidationError
from django_ledger.models.unit import EntityUnitModel
from django_ledger.models.vendor import VendorModel
from django_ledger.settings import (
    DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING,
    DJANGO_LEDGER_RECEIPT_NUMBER_PREFIX,
)


class ReceiptConfigureAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_receipt_configure_user",
            email="api-receipt-configure-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Receipt Configure Entity", fy_start_month=1):
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
        customer_model.refresh_from_db()

        vendor_model = VendorModel(
            vendor_name=f"{name} Vendor",
            entity_model=entity_model,
            description=f"{name} Vendor description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()
        vendor_model.refresh_from_db()

        unit_model = EntityUnitModel.add_root(
            name=f"{name} Unit",
            slug=f"{slugify(name)}-unit",
            entity=entity_model,
            document_prefix="RCU",
            active=True,
            hidden=False,
        )

        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
            "income_account": income_account,
            "expense_account": expense_account,
            "transfer_account": transfer_account,
            "customer_model": customer_model,
            "vendor_model": vendor_model,
            "unit_model": unit_model,
        }

    def configure_sales_receipt(self, setup, *, entity_input=None, customer_input=None, unit_input=None, commit=True):
        receipt_model = ReceiptModel()
        receipt_model.configure(
            entity_model=entity_input or setup["entity_model"],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            amount=Decimal("125.00"),
            unit_model=unit_input,
            receipt_date=date(2026, 1, 15),
            customer_model=customer_input or setup["customer_model"],
            charge_account=setup["cash_account"],
            receipt_account=setup["income_account"],
            commit=commit,
        )
        if commit:
            receipt_model.refresh_from_db()
        return receipt_model

    def configure_expense_receipt(self, setup, *, vendor_input=None):
        receipt_model = ReceiptModel()
        receipt_model.configure(
            entity_model=setup["entity_model"],
            receipt_type=ReceiptModel.EXPENSE_RECEIPT,
            amount=Decimal("75.00"),
            receipt_date=date(2026, 1, 15),
            vendor_model=vendor_input or setup["vendor_model"],
            charge_account=setup["cash_account"],
            receipt_account=setup["expense_account"],
            commit=True,
        )
        receipt_model.refresh_from_db()
        return receipt_model

    def create_numberable_receipt(self, setup, *, saved=False):
        ledger_model = setup["entity_model"].create_ledger(
            name="API Receipt Numbering Ledger",
            posted=True,
            commit=True,
        )
        receipt_kwargs = {
            "receipt_number": "",
            "receipt_date": date(2026, 1, 15),
            "receipt_type": ReceiptModel.SALES_RECEIPT,
            "ledger_model": ledger_model,
            "customer_model": setup["customer_model"],
            "charge_account": setup["cash_account"],
            "receipt_account": setup["income_account"],
            "amount": Decimal("10.00"),
        }
        if saved:
            return ReceiptModel.objects.create(**receipt_kwargs)
        return ReceiptModel(**receipt_kwargs)

    def assert_receipt_number(self, number, *, fiscal_year, sequence):
        self.assertTrue(number)
        self.assertTrue(number.startswith(f"{DJANGO_LEDGER_RECEIPT_NUMBER_PREFIX}-{fiscal_year}-"))
        self.assertTrue(str(number).endswith(str(sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)))

    def test_configure_accepts_entity_model_slug_and_uuid(self):
        setup = self.create_entity_setup()
        entity_model = setup["entity_model"]

        by_model = self.configure_sales_receipt(setup, entity_input=entity_model)
        by_slug = self.configure_sales_receipt(setup, entity_input=entity_model.slug)
        by_uuid = self.configure_sales_receipt(setup, entity_input=entity_model.uuid)

        for receipt_model in [by_model, by_slug, by_uuid]:
            self.assertEqual(receipt_model.ledger_model.entity_id, entity_model.uuid)
            self.assertEqual(receipt_model.customer_model_id, setup["customer_model"].uuid)
            self.assertTrue(receipt_model.receipt_number)

    def test_configure_commit_false_configures_in_memory_receipt_and_persists_only_ledger(self):
        setup = self.create_entity_setup(name="API Receipt Configure Commit False Entity")

        receipt_model = self.configure_sales_receipt(setup, commit=False)

        self.assertTrue(receipt_model.is_configured())
        self.assertTrue(receipt_model.receipt_number)
        self.assertIsNotNone(receipt_model.ledger_model_id)
        self.assertFalse(ReceiptModel.objects.filter(uuid=receipt_model.uuid).exists())
        self.assertTrue(receipt_model.ledger_model.__class__.objects.filter(uuid=receipt_model.ledger_model_id).exists())

    def test_configure_accepts_customer_number_and_uuid(self):
        setup = self.create_entity_setup(name="API Receipt Configure Customer Entity")
        customer_model = setup["customer_model"]

        by_number = self.configure_sales_receipt(setup, customer_input=customer_model.customer_number)
        by_uuid = self.configure_sales_receipt(setup, customer_input=customer_model.uuid)

        self.assertEqual(by_number.customer_model_id, customer_model.uuid)
        self.assertEqual(by_uuid.customer_model_id, customer_model.uuid)

    def test_configure_accepts_vendor_number_and_uuid(self):
        setup = self.create_entity_setup(name="API Receipt Configure Vendor Entity")
        vendor_model = setup["vendor_model"]

        by_number = self.configure_expense_receipt(setup, vendor_input=vendor_model.vendor_number)
        by_uuid = self.configure_expense_receipt(setup, vendor_input=vendor_model.uuid)

        self.assertEqual(by_number.vendor_model_id, vendor_model.uuid)
        self.assertEqual(by_uuid.vendor_model_id, vendor_model.uuid)

    def test_configure_accepts_unit_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API Receipt Configure Unit Entity")
        unit_model = setup["unit_model"]

        by_instance = self.configure_sales_receipt(setup, unit_input=unit_model)
        by_slug = self.configure_sales_receipt(setup, unit_input=unit_model.slug)
        by_uuid = self.configure_sales_receipt(setup, unit_input=unit_model.uuid)

        self.assertEqual(by_instance.unit_model_id, unit_model.uuid)
        self.assertEqual(by_slug.unit_model_id, unit_model.uuid)
        self.assertEqual(by_uuid.unit_model_id, unit_model.uuid)

    def test_generate_receipt_number_commit_false_and_commit_true(self):
        setup = self.create_entity_setup(name="API Receipt Configure Numbering Entity")
        fy_key = setup["entity_model"].get_fy_for_date(dt=date(2026, 1, 15))

        unsaved_receipt = self.create_numberable_receipt(setup, saved=False)

        self.assertTrue(unsaved_receipt.can_generate_receipt_number())

        first_number = unsaved_receipt.generate_receipt_number(commit=False)

        self.assert_receipt_number(first_number, fiscal_year=fy_key, sequence=1)
        self.assertFalse(ReceiptModel.objects.filter(uuid=unsaved_receipt.uuid).exists())

        saved_receipt = self.create_numberable_receipt(setup, saved=True)
        second_number = saved_receipt.generate_receipt_number(commit=True)
        saved_receipt.refresh_from_db()

        self.assert_receipt_number(second_number, fiscal_year=fy_key, sequence=2)
        self.assertEqual(saved_receipt.receipt_number, second_number)
        self.assertFalse(saved_receipt.can_generate_receipt_number())

    def test_configure_rejects_customer_vendor_mutual_exclusion(self):
        setup = self.create_entity_setup(name="API Receipt Configure Invalid Entity")
        receipt_model = ReceiptModel()

        with self.assertRaises(ReceiptModelValidationError):
            receipt_model.configure(
                entity_model=setup["entity_model"],
                receipt_type=ReceiptModel.SALES_RECEIPT,
                amount=Decimal("25.00"),
                receipt_date=date(2026, 1, 15),
                customer_model=setup["customer_model"],
                vendor_model=setup["vendor_model"],
                charge_account=setup["cash_account"],
                receipt_account=setup["income_account"],
                commit=True,
            )
