"""
High-level API tests for ReceiptModel queryset and manager behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import ReceiptModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.receipt import ReceiptModelValidationError
from django_ledger.models.vendor import VendorModel


class ReceiptQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_receipt_queryset_admin",
            email="api-receipt-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_receipt_queryset_manager",
            email="api-receipt-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_receipt_queryset_other_admin",
            email="api-receipt-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_receipt_queryset_unrelated",
            email="api-receipt-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_receipt_queryset_superuser",
            email="api-receipt-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Receipt Queryset Entity", admin_user=None, manager_user=None):
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

        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
            "income_account": income_account,
            "expense_account": expense_account,
            "customer_model": customer_model,
            "vendor_model": vendor_model,
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

    def assert_receipt_uuids(self, queryset, expected_receipts):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {receipt.uuid for receipt in expected_receipts},
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API Receipt Queryset Entity A")
        other_setup = self.create_entity_setup(
            name="API Receipt Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        receipt_model = self.create_sales_receipt(setup)
        self.create_sales_receipt(other_setup)

        entity_model = setup["entity_model"]

        self.assert_receipt_uuids(ReceiptModel.objects.for_entity(entity_model), [receipt_model])
        self.assert_receipt_uuids(ReceiptModel.objects.for_entity(entity_model.slug), [receipt_model])
        self.assert_receipt_uuids(ReceiptModel.objects.for_entity(entity_model.uuid), [receipt_model])

    def test_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_sales_receipt(self.create_entity_setup())

        with self.assertRaises(ReceiptModelValidationError):
            ReceiptModel.objects.for_entity(object())

        self.assertFalse(ReceiptModel.objects.for_entity("missing-receipt-entity-slug").exists())

    def test_for_user_scopes_to_admin_manager_and_current_superuser_behavior(self):
        setup = self.create_entity_setup(
            name="API Receipt Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_setup = self.create_entity_setup(
            name="API Receipt Queryset Other Access Entity",
            admin_user=self.other_admin_user,
        )
        receipt_model = self.create_sales_receipt(setup)
        other_receipt_model = self.create_sales_receipt(other_setup)

        self.assert_receipt_uuids(ReceiptModel.objects.all().for_user(self.admin_user), [receipt_model])
        self.assert_receipt_uuids(ReceiptModel.objects.all().for_user(self.manager_user), [receipt_model])
        self.assertFalse(ReceiptModel.objects.all().for_user(self.unrelated_user).exists())

        superuser_qs = ReceiptModel.objects.all().for_user(self.superuser)
        self.assertFalse(superuser_qs.filter(uuid=receipt_model.uuid).exists())
        self.assertFalse(superuser_qs.filter(uuid=other_receipt_model.uuid).exists())

    def test_for_customer_accepts_model_number_and_uuid(self):
        setup = self.create_entity_setup(name="API Receipt Queryset Customer Entity")
        sales_receipt = self.create_sales_receipt(setup)
        self.create_expense_receipt(setup)
        customer_model = setup["customer_model"]
        receipts_qs = ReceiptModel.objects.for_entity(setup["entity_model"])

        self.assert_receipt_uuids(receipts_qs.for_customer(customer_model), [sales_receipt])
        self.assert_receipt_uuids(receipts_qs.for_customer(customer_model.customer_number), [sales_receipt])
        self.assert_receipt_uuids(receipts_qs.for_customer(customer_model.uuid), [sales_receipt])

    def test_for_vendor_accepts_model_number_and_uuid(self):
        setup = self.create_entity_setup(name="API Receipt Queryset Vendor Entity")
        self.create_sales_receipt(setup)
        expense_receipt = self.create_expense_receipt(setup)
        vendor_model = setup["vendor_model"]
        receipts_qs = ReceiptModel.objects.for_entity(setup["entity_model"])

        self.assert_receipt_uuids(receipts_qs.for_vendor(vendor_model), [expense_receipt])
        self.assert_receipt_uuids(receipts_qs.for_vendor(vendor_model.vendor_number), [expense_receipt])
        self.assert_receipt_uuids(receipts_qs.for_vendor(vendor_model.uuid), [expense_receipt])

    def test_for_dates_uses_inclusive_boundaries(self):
        setup = self.create_entity_setup(name="API Receipt Queryset Date Entity")
        start_receipt = self.create_sales_receipt(
            setup,
            receipt_date=date(2026, 1, 1),
            amount="10.00",
        )
        end_receipt = self.create_sales_receipt(
            setup,
            receipt_date=date(2026, 1, 31),
            amount="20.00",
        )
        self.create_sales_receipt(
            setup,
            receipt_date=date(2026, 2, 1),
            amount="30.00",
        )

        january_qs = ReceiptModel.objects.for_entity(setup["entity_model"]).for_dates(
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )

        self.assert_receipt_uuids(january_qs, [start_receipt, end_receipt])
