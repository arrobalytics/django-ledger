"""
High-level API behavior tests for EntityModel customer and vendor wrappers.

These tests cover entity-scoped commercial-party creation, lookup, active
filtering, and customer validation without requiring accounting fixtures.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.entity import EntityModel, EntityModelValidationError


class EntityCustomerVendorAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_entity_customer_vendor_admin",
            email="api-entity-customer-vendor-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_entity_customer_vendor_other_admin",
            email="api-entity-customer-vendor-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Entity Customer Vendor Entity", admin=None):
        return EntityModel.create_entity(
            name=name,
            admin=admin or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_customer(self, entity_model, *, name="API Entity Customer", active=True):
        return entity_model.create_customer(
            {
                "customer_name": name,
                "description": f"{name} description",
                "active": active,
                "hidden": False,
            }
        )

    def create_vendor(self, entity_model, *, name="API Entity Vendor", active=True):
        return entity_model.create_vendor(
            {
                "vendor_name": name,
                "description": f"{name} description",
                "active": active,
                "hidden": False,
            }
        )

    def test_create_customer_creates_active_customer_with_generated_number(self):
        entity_model = self.create_entity()

        customer_model = self.create_customer(entity_model)

        self.assertEqual(customer_model.entity_model_id, entity_model.uuid)
        self.assertTrue(customer_model.active)
        self.assertTrue(customer_model.customer_number)
        self.assertIsInstance(customer_model.customer_number, str)

    def test_create_vendor_creates_active_vendor_with_generated_number(self):
        entity_model = self.create_entity()

        vendor_model = self.create_vendor(entity_model)

        self.assertEqual(vendor_model.entity_model_id, entity_model.uuid)
        self.assertTrue(vendor_model.active)
        self.assertTrue(vendor_model.vendor_number)
        self.assertIsInstance(vendor_model.vendor_number, str)

    def test_get_customers_is_entity_scoped_and_filters_inactive_by_default(self):
        entity_model = self.create_entity(name="API Customer Scoped Entity")
        other_entity = self.create_entity(
            name="API Other Customer Scoped Entity",
            admin=self.other_admin_user,
        )

        active_customer = self.create_customer(
            entity_model,
            name="API Active Entity Customer",
        )
        inactive_customer = self.create_customer(
            entity_model,
            name="API Inactive Entity Customer",
            active=False,
        )
        other_customer = self.create_customer(
            other_entity,
            name="API Other Entity Customer",
        )

        default_customer_qs = entity_model.get_customers()
        all_customer_qs = entity_model.get_customers(active=False)

        self.assertTrue(default_customer_qs.filter(uuid=active_customer.uuid).exists())
        self.assertFalse(default_customer_qs.filter(uuid=inactive_customer.uuid).exists())
        self.assertFalse(default_customer_qs.filter(uuid=other_customer.uuid).exists())

        self.assertTrue(all_customer_qs.filter(uuid=active_customer.uuid).exists())
        self.assertTrue(all_customer_qs.filter(uuid=inactive_customer.uuid).exists())
        self.assertFalse(all_customer_qs.filter(uuid=other_customer.uuid).exists())

    def test_get_vendors_is_entity_scoped_and_filters_inactive_by_default(self):
        entity_model = self.create_entity(name="API Vendor Scoped Entity")
        other_entity = self.create_entity(
            name="API Other Vendor Scoped Entity",
            admin=self.other_admin_user,
        )

        active_vendor = self.create_vendor(
            entity_model,
            name="API Active Entity Vendor",
        )
        inactive_vendor = self.create_vendor(
            entity_model,
            name="API Inactive Entity Vendor",
            active=False,
        )
        other_vendor = self.create_vendor(
            other_entity,
            name="API Other Entity Vendor",
        )

        default_vendor_qs = entity_model.get_vendors()
        all_vendor_qs = entity_model.get_vendors(active=False)

        self.assertTrue(default_vendor_qs.filter(uuid=active_vendor.uuid).exists())
        self.assertFalse(default_vendor_qs.filter(uuid=inactive_vendor.uuid).exists())
        self.assertFalse(default_vendor_qs.filter(uuid=other_vendor.uuid).exists())

        self.assertTrue(all_vendor_qs.filter(uuid=active_vendor.uuid).exists())
        self.assertTrue(all_vendor_qs.filter(uuid=inactive_vendor.uuid).exists())
        self.assertFalse(all_vendor_qs.filter(uuid=other_vendor.uuid).exists())

    def test_get_customer_by_number_and_uuid_return_expected_customer(self):
        entity_model = self.create_entity(name="API Customer Lookup Entity")
        other_entity = self.create_entity(
            name="API Other Customer Lookup Entity",
            admin=self.other_admin_user,
        )

        customer_model = self.create_customer(
            entity_model,
            name="API Lookup Entity Customer",
        )
        other_customer = self.create_customer(
            other_entity,
            name="API Other Lookup Entity Customer",
        )

        by_number = entity_model.get_customer_by_number(customer_model.customer_number)
        by_uuid = entity_model.get_customer_by_uuid(str(customer_model.uuid))

        self.assertEqual(by_number.uuid, customer_model.uuid)
        self.assertEqual(by_uuid.uuid, customer_model.uuid)
        self.assertFalse(
            entity_model.get_customers().filter(uuid=other_customer.uuid).exists()
        )

    def test_get_vendor_by_number_and_uuid_return_expected_vendor(self):
        entity_model = self.create_entity(name="API Vendor Lookup Entity")
        other_entity = self.create_entity(
            name="API Other Vendor Lookup Entity",
            admin=self.other_admin_user,
        )

        vendor_model = self.create_vendor(
            entity_model,
            name="API Lookup Entity Vendor",
        )
        other_vendor = self.create_vendor(
            other_entity,
            name="API Other Lookup Entity Vendor",
        )

        by_number = entity_model.get_vendor_by_number(vendor_model.vendor_number)
        by_uuid = entity_model.get_vendor_by_uuid(str(vendor_model.uuid))

        self.assertEqual(by_number.uuid, vendor_model.uuid)
        self.assertEqual(by_uuid.uuid, vendor_model.uuid)
        self.assertFalse(
            entity_model.get_vendors().filter(uuid=other_vendor.uuid).exists()
        )

    def test_validate_customer_accepts_same_entity_and_rejects_other_entity_customer(self):
        entity_model = self.create_entity(name="API Customer Validation Entity")
        other_entity = self.create_entity(
            name="API Other Customer Validation Entity",
            admin=self.other_admin_user,
        )

        customer_model = self.create_customer(
            entity_model,
            name="API Validated Entity Customer",
        )
        other_customer = self.create_customer(
            other_entity,
            name="API Rejected Entity Customer",
        )

        self.assertIsNone(entity_model.validate_customer(customer_model))

        with self.assertRaises(EntityModelValidationError):
            entity_model.validate_customer(other_customer)
