"""
High-level API tests for CustomerModel and VendorModel validation behavior.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from django_ledger.models.customer import CustomerModel, CustomerModelValidationError
from django_ledger.models.entity import EntityModel
from django_ledger.models.vendor import VendorModel, VendorModelValidationError


class CustomerVendorValidationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_customer_vendor_validation_admin",
            email="api-customer-vendor-validation-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Customer Vendor Validation Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def make_customer(self, entity_model, *, name="API Validation Customer", **kwargs):
        return CustomerModel(
            customer_name=name,
            entity_model=entity_model,
            description=f"{name} description",
            **kwargs,
        )

    def make_vendor(self, entity_model, *, name="API Validation Vendor", **kwargs):
        return VendorModel(
            vendor_name=name,
            entity_model=entity_model,
            description=f"{name} description",
            **kwargs,
        )

    def create_customer(self, entity_model, *, name="API Validation Customer", **kwargs):
        customer_model = self.make_customer(entity_model, name=name, **kwargs)
        customer_model.full_clean()
        customer_model.save()
        return customer_model

    def create_vendor(self, entity_model, *, name="API Validation Vendor", **kwargs):
        vendor_model = self.make_vendor(entity_model, name=name, **kwargs)
        vendor_model.full_clean()
        vendor_model.save()
        return vendor_model

    def test_customer_validate_for_entity_accepts_same_entity_and_rejects_other_entity(self):
        entity_model = self.create_entity(name="API Customer Validation Entity A")
        other_entity_model = self.create_entity(name="API Customer Validation Entity B")
        customer_model = self.create_customer(entity_model)

        self.assertIsNone(customer_model.validate_for_entity(entity_model))

        with self.assertRaises(CustomerModelValidationError):
            customer_model.validate_for_entity(other_entity_model)

    def test_customer_validate_for_entity_rejects_invalid_input(self):
        customer_model = self.create_customer(self.create_entity())

        with self.assertRaises(CustomerModelValidationError):
            customer_model.validate_for_entity(object())

    def test_vendor_validate_for_entity_accepts_model_slug_and_uuid(self):
        entity_model = self.create_entity()
        vendor_model = self.create_vendor(entity_model)

        self.assertIsNone(vendor_model.validate_for_entity(entity_model))
        self.assertIsNone(vendor_model.validate_for_entity(entity_model.slug))
        self.assertIsNone(vendor_model.validate_for_entity(entity_model.uuid))

    def test_vendor_validate_for_entity_rejects_other_entity_and_invalid_input(self):
        entity_model = self.create_entity(name="API Vendor Validation Entity A")
        other_entity_model = self.create_entity(name="API Vendor Validation Entity B")
        vendor_model = self.create_vendor(entity_model)

        with self.assertRaises(VendorModelValidationError):
            vendor_model.validate_for_entity(other_entity_model)
        with self.assertRaises(VendorModelValidationError):
            vendor_model.validate_for_entity(other_entity_model.slug)
        with self.assertRaises(VendorModelValidationError):
            vendor_model.validate_for_entity(other_entity_model.uuid)
        with self.assertRaises(VendorModelValidationError):
            vendor_model.validate_for_entity(object())

    def test_customer_and_vendor_reject_address_line_two_without_address_line_one(self):
        entity_model = self.create_entity()
        customer_model = self.make_customer(entity_model, address_2="Suite 200")
        vendor_model = self.make_vendor(entity_model, address_2="Suite 300")

        with self.assertRaises(ValidationError):
            customer_model.full_clean()
        with self.assertRaises(ValidationError):
            vendor_model.full_clean()

    def test_customer_and_vendor_accept_complete_address_lines(self):
        entity_model = self.create_entity()
        customer_model = self.make_customer(
            entity_model,
            address_1="123 Customer Street",
            address_2="Suite 200",
        )
        vendor_model = self.make_vendor(
            entity_model,
            address_1="456 Vendor Avenue",
            address_2="Suite 300",
        )

        customer_model.full_clean()
        vendor_model.full_clean()

        self.assertTrue(customer_model.customer_number)
        self.assertTrue(vendor_model.vendor_number)

    def test_customer_sales_tax_rate_validation_accepts_valid_and_rejects_out_of_range(self):
        entity_model = self.create_entity()

        self.make_customer(entity_model, sales_tax_rate=0.25).full_clean()

        with self.assertRaises(ValidationError):
            self.make_customer(entity_model, sales_tax_rate=-0.01).full_clean()
        with self.assertRaises(ValidationError):
            self.make_customer(entity_model, sales_tax_rate=1.01).full_clean()

    def test_vendor_tax_and_financial_account_info_smoke_behavior(self):
        entity_model = self.create_entity()
        vendor_model = self.make_vendor(
            entity_model,
            tax_id_number="TAX-12345",
            account_number="000123456789",
            routing_number="000111222",
            account_type=VendorModel.ACCOUNT_CHECKING,
        )

        vendor_model.full_clean()

        self.assertEqual(vendor_model.tax_id_number, "TAX-12345")
        self.assertEqual(vendor_model.get_account_last_digits(), "*6789")
        self.assertEqual(vendor_model.get_routing_last_digits(), "*1222")
        self.assertEqual(vendor_model.get_account_type_display(), "Checking")

        with self.assertRaises(ValidationError):
            self.make_vendor(entity_model, account_number="12-34").full_clean()
