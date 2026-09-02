"""
High-level API tests for EntityModel customer and vendor factory helpers.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.vendor import VendorModel
from django_ledger.settings import (
    DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX,
    DJANGO_LEDGER_VENDOR_NUMBER_PREFIX,
)


class CustomerVendorFactoryAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_customer_vendor_factory_admin",
            email="api-customer-vendor-factory-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Customer Vendor Factory Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def customer_kwargs(self, *, name="API Factory Customer"):
        return {
            "customer_name": name,
            "description": f"{name} description",
        }

    def vendor_kwargs(self, *, name="API Factory Vendor"):
        return {
            "vendor_name": name,
            "description": f"{name} description",
        }

    def assert_number_present(self, number, prefix):
        self.assertTrue(number)
        self.assertTrue(number.startswith(f"{prefix}-"))

    def test_create_customer_commit_false_returns_unsaved_configured_customer(self):
        entity_model = self.create_entity()

        customer_model = entity_model.create_customer(
            self.customer_kwargs(),
            commit=False,
        )

        self.assertIsInstance(customer_model, CustomerModel)
        self.assertEqual(customer_model.entity_model_id, entity_model.uuid)
        self.assert_number_present(
            customer_model.customer_number,
            DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX,
        )
        self.assertTrue(customer_model.active)
        self.assertFalse(customer_model.hidden)
        self.assertFalse(CustomerModel.objects.filter(uuid=customer_model.uuid).exists())

    def test_create_vendor_commit_false_returns_unsaved_configured_vendor(self):
        entity_model = self.create_entity()

        vendor_model = entity_model.create_vendor(
            self.vendor_kwargs(),
            commit=False,
        )

        self.assertIsInstance(vendor_model, VendorModel)
        self.assertEqual(vendor_model.entity_model_id, entity_model.uuid)
        self.assert_number_present(
            vendor_model.vendor_number,
            DJANGO_LEDGER_VENDOR_NUMBER_PREFIX,
        )
        self.assertTrue(vendor_model.active)
        self.assertFalse(vendor_model.hidden)
        self.assertFalse(VendorModel.objects.filter(uuid=vendor_model.uuid).exists())

    def test_create_customer_commit_true_persists_customer(self):
        entity_model = self.create_entity()

        customer_model = entity_model.create_customer(
            self.customer_kwargs(name="API Persisted Factory Customer"),
            commit=True,
        )

        customer_model.refresh_from_db()
        self.assertEqual(customer_model.entity_model_id, entity_model.uuid)
        self.assert_number_present(
            customer_model.customer_number,
            DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX,
        )
        self.assertTrue(customer_model.active)
        self.assertFalse(customer_model.hidden)
        self.assertTrue(CustomerModel.objects.filter(uuid=customer_model.uuid).exists())

    def test_create_vendor_commit_true_persists_vendor(self):
        entity_model = self.create_entity()

        vendor_model = entity_model.create_vendor(
            self.vendor_kwargs(name="API Persisted Factory Vendor"),
            commit=True,
        )

        vendor_model.refresh_from_db()
        self.assertEqual(vendor_model.entity_model_id, entity_model.uuid)
        self.assert_number_present(
            vendor_model.vendor_number,
            DJANGO_LEDGER_VENDOR_NUMBER_PREFIX,
        )
        self.assertTrue(vendor_model.active)
        self.assertFalse(vendor_model.hidden)
        self.assertTrue(VendorModel.objects.filter(uuid=vendor_model.uuid).exists())
