"""
High-level API behavior tests for CustomerModel and VendorModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.vendor import VendorModel


class CustomerVendorHighLevelAPITest(TestCase):
    """
    High-level behavior tests for CustomerModel and VendorModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic commercial-party API invariants that
    should remain true across refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_customer_vendor_contract_user",
            email="api-customer-vendor-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Customer Vendor Contract Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        entity_model.create_chart_of_accounts(
            coa_name="API Customer Vendor Contract CoA",
            commit=True,
            assign_as_default=True,
        )

        entity_model.refresh_from_db()
        return entity_model

    def create_customer(self, entity_model, *, name="API Contract Customer"):
        customer_model = CustomerModel(
            customer_name=name,
            entity_model=entity_model,
            description=f"{name} description",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        return customer_model

    def create_vendor(self, entity_model, *, name="API Contract Vendor"):
        vendor_model = VendorModel(
            vendor_name=name,
            entity_model=entity_model,
            description=f"{name} description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()
        return vendor_model

    def test_customer_is_created_under_entity_context(self):
        entity_model = self.create_entity()

        customer_model = self.create_customer(entity_model)

        self.assertIsNotNone(customer_model.uuid)
        self.assertEqual(customer_model.entity_model_id, entity_model.uuid)
        self.assertEqual(customer_model.customer_name, "API Contract Customer")
        self.assertTrue(customer_model.active)
        self.assertFalse(customer_model.hidden)

    def test_customer_number_is_generated_on_save(self):
        entity_model = self.create_entity()

        customer_model = self.create_customer(entity_model)

        self.assertTrue(customer_model.customer_number)
        self.assertIsInstance(customer_model.customer_number, str)

    def test_customer_for_entity_limits_queryset_to_entity_scope(self):
        entity_model = self.create_entity(name="API Customer Entity A")
        other_entity_model = self.create_entity(name="API Customer Entity B")

        customer_model = self.create_customer(
            entity_model,
            name="API Contract Customer A",
        )
        other_customer_model = self.create_customer(
            other_entity_model,
            name="API Contract Customer B",
        )

        scoped_qs = CustomerModel.objects.for_entity(entity_model)

        self.assertTrue(scoped_qs.filter(uuid=customer_model.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_customer_model.uuid).exists())

    def test_customer_active_inactive_queryset_helpers(self):
        entity_model = self.create_entity()

        active_customer = self.create_customer(
            entity_model,
            name="API Active Customer",
        )

        inactive_customer = self.create_customer(
            entity_model,
            name="API Inactive Customer",
        )
        inactive_customer.active = False
        inactive_customer.save(update_fields=["active"])

        customers_qs = CustomerModel.objects.for_entity(entity_model)

        self.assertTrue(customers_qs.active().filter(uuid=active_customer.uuid).exists())
        self.assertFalse(customers_qs.active().filter(uuid=inactive_customer.uuid).exists())

        self.assertTrue(customers_qs.inactive().filter(uuid=inactive_customer.uuid).exists())
        self.assertFalse(customers_qs.inactive().filter(uuid=active_customer.uuid).exists())

    def test_customer_visible_hidden_queryset_helpers(self):
        entity_model = self.create_entity()

        visible_customer = self.create_customer(
            entity_model,
            name="API Visible Customer",
        )

        hidden_customer = self.create_customer(
            entity_model,
            name="API Hidden Customer",
        )
        hidden_customer.hidden = True
        hidden_customer.save(update_fields=["hidden"])

        customers_qs = CustomerModel.objects.for_entity(entity_model)

        self.assertTrue(customers_qs.visible().filter(uuid=visible_customer.uuid).exists())
        self.assertFalse(customers_qs.visible().filter(uuid=hidden_customer.uuid).exists())

        self.assertTrue(customers_qs.hidden().filter(uuid=hidden_customer.uuid).exists())
        self.assertFalse(customers_qs.hidden().filter(uuid=visible_customer.uuid).exists())

    def test_vendor_is_created_under_entity_context(self):
        entity_model = self.create_entity()

        vendor_model = self.create_vendor(entity_model)

        self.assertIsNotNone(vendor_model.uuid)
        self.assertEqual(vendor_model.entity_model_id, entity_model.uuid)
        self.assertEqual(vendor_model.vendor_name, "API Contract Vendor")
        self.assertTrue(vendor_model.active)
        self.assertFalse(vendor_model.hidden)

    def test_vendor_number_is_generated_on_save(self):
        entity_model = self.create_entity()

        vendor_model = self.create_vendor(entity_model)

        self.assertTrue(vendor_model.vendor_number)
        self.assertIsInstance(vendor_model.vendor_number, str)

    def test_vendor_for_entity_limits_queryset_to_entity_scope(self):
        entity_model = self.create_entity(name="API Vendor Entity A")
        other_entity_model = self.create_entity(name="API Vendor Entity B")

        vendor_model = self.create_vendor(
            entity_model,
            name="API Contract Vendor A",
        )
        other_vendor_model = self.create_vendor(
            other_entity_model,
            name="API Contract Vendor B",
        )

        scoped_qs = VendorModel.objects.for_entity(entity_model)

        self.assertTrue(scoped_qs.filter(uuid=vendor_model.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_vendor_model.uuid).exists())

    def test_vendor_active_inactive_queryset_helpers(self):
        entity_model = self.create_entity()

        active_vendor = self.create_vendor(
            entity_model,
            name="API Active Vendor",
        )

        inactive_vendor = self.create_vendor(
            entity_model,
            name="API Inactive Vendor",
        )
        inactive_vendor.active = False
        inactive_vendor.save(update_fields=["active"])

        vendors_qs = VendorModel.objects.for_entity(entity_model)

        self.assertTrue(vendors_qs.active().filter(uuid=active_vendor.uuid).exists())
        self.assertFalse(vendors_qs.active().filter(uuid=inactive_vendor.uuid).exists())

        self.assertTrue(vendors_qs.inactive().filter(uuid=inactive_vendor.uuid).exists())
        self.assertFalse(vendors_qs.inactive().filter(uuid=active_vendor.uuid).exists())

    def test_vendor_visible_hidden_queryset_helpers(self):
        entity_model = self.create_entity()

        visible_vendor = self.create_vendor(
            entity_model,
            name="API Visible Vendor",
        )

        hidden_vendor = self.create_vendor(
            entity_model,
            name="API Hidden Vendor",
        )
        hidden_vendor.hidden = True
        hidden_vendor.save(update_fields=["hidden"])

        vendors_qs = VendorModel.objects.for_entity(entity_model)

        self.assertTrue(vendors_qs.visible().filter(uuid=visible_vendor.uuid).exists())
        self.assertFalse(vendors_qs.visible().filter(uuid=hidden_vendor.uuid).exists())

        self.assertTrue(vendors_qs.hidden().filter(uuid=hidden_vendor.uuid).exists())
        self.assertFalse(vendors_qs.hidden().filter(uuid=visible_vendor.uuid).exists())
