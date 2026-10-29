"""
High-level API tests for CustomerModel and VendorModel queryset behavior.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.customer import CustomerModel, CustomerModelValidationError
from django_ledger.models.entity import EntityModel
from django_ledger.models.vendor import VendorModel, VendorModelValidationError


class CustomerVendorQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_customer_vendor_queryset_admin",
            email="api-customer-vendor-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_customer_vendor_queryset_manager",
            email="api-customer-vendor-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_customer_vendor_queryset_other_admin",
            email="api-customer-vendor-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_customer_vendor_queryset_unrelated",
            email="api-customer-vendor-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_customer_vendor_queryset_superuser",
            email="api-customer-vendor-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Customer Vendor Queryset Entity", admin_user=None, manager_user=None):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=admin_user or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        if manager_user is not None:
            entity_model.managers.add(manager_user)
        return entity_model

    def create_customer(
        self,
        entity_model,
        *,
        name="API Queryset Customer",
        active=True,
        hidden=False,
    ):
        customer_model = CustomerModel(
            customer_name=name,
            entity_model=entity_model,
            description=f"{name} description",
            active=active,
            hidden=hidden,
        )
        customer_model.full_clean()
        customer_model.save()
        return customer_model

    def create_vendor(
        self,
        entity_model,
        *,
        name="API Queryset Vendor",
        active=True,
        hidden=False,
    ):
        vendor_model = VendorModel(
            vendor_name=name,
            entity_model=entity_model,
            description=f"{name} description",
            active=active,
            hidden=hidden,
        )
        vendor_model.full_clean()
        vendor_model.save()
        return vendor_model

    def assert_customer_uuids(self, queryset, expected_customers):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {customer_model.uuid for customer_model in expected_customers},
        )

    def assert_vendor_uuids(self, queryset, expected_vendors):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {vendor_model.uuid for vendor_model in expected_vendors},
        )

    def test_customer_for_entity_accepts_model_slug_and_uuid(self):
        entity_model = self.create_entity(name="API Customer Queryset Entity A")
        other_entity_model = self.create_entity(
            name="API Customer Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        customer_model = self.create_customer(entity_model, name="API Entity A Customer")
        self.create_customer(other_entity_model, name="API Entity B Customer")

        self.assert_customer_uuids(CustomerModel.objects.for_entity(entity_model), [customer_model])
        self.assert_customer_uuids(CustomerModel.objects.for_entity(entity_model.slug), [customer_model])
        self.assert_customer_uuids(CustomerModel.objects.for_entity(entity_model.uuid), [customer_model])

    def test_customer_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_customer(self.create_entity())

        with self.assertRaises(CustomerModelValidationError):
            CustomerModel.objects.for_entity(object())

        self.assertFalse(CustomerModel.objects.for_entity("missing-customer-entity-slug").exists())

    def test_vendor_for_entity_accepts_model_slug_and_uuid(self):
        entity_model = self.create_entity(name="API Vendor Queryset Entity A")
        other_entity_model = self.create_entity(
            name="API Vendor Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        vendor_model = self.create_vendor(entity_model, name="API Entity A Vendor")
        self.create_vendor(other_entity_model, name="API Entity B Vendor")

        self.assert_vendor_uuids(VendorModel.objects.for_entity(entity_model), [vendor_model])
        self.assert_vendor_uuids(VendorModel.objects.for_entity(entity_model.slug), [vendor_model])
        self.assert_vendor_uuids(VendorModel.objects.for_entity(entity_model.uuid), [vendor_model])

    def test_vendor_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_vendor(self.create_entity())

        with self.assertRaises(VendorModelValidationError):
            VendorModel.objects.for_entity(object())

        self.assertFalse(VendorModel.objects.for_entity("missing-vendor-entity-slug").exists())

    def test_customer_for_user_scopes_to_authorized_users_and_superuser(self):
        entity_model = self.create_entity(
            name="API Customer Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_entity_model = self.create_entity(
            name="API Customer Queryset Other Access Entity",
            admin_user=self.other_admin_user,
        )
        customer_model = self.create_customer(entity_model, name="API Access Customer")
        other_customer_model = self.create_customer(other_entity_model, name="API Other Access Customer")

        self.assert_customer_uuids(CustomerModel.objects.all().for_user(self.admin_user), [customer_model])
        self.assert_customer_uuids(CustomerModel.objects.all().for_user(self.manager_user), [customer_model])
        self.assertFalse(CustomerModel.objects.all().for_user(self.unrelated_user).exists())
        self.assert_customer_uuids(
            CustomerModel.objects.all().for_user(self.superuser),
            [customer_model, other_customer_model],
        )

    def test_vendor_for_user_scopes_to_authorized_users_and_superuser(self):
        entity_model = self.create_entity(
            name="API Vendor Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_entity_model = self.create_entity(
            name="API Vendor Queryset Other Access Entity",
            admin_user=self.other_admin_user,
        )
        vendor_model = self.create_vendor(entity_model, name="API Access Vendor")
        other_vendor_model = self.create_vendor(other_entity_model, name="API Other Access Vendor")

        self.assert_vendor_uuids(VendorModel.objects.all().for_user(self.admin_user), [vendor_model])
        self.assert_vendor_uuids(VendorModel.objects.all().for_user(self.manager_user), [vendor_model])
        self.assertFalse(VendorModel.objects.all().for_user(self.unrelated_user).exists())
        self.assert_vendor_uuids(
            VendorModel.objects.all().for_user(self.superuser),
            [vendor_model, other_vendor_model],
        )

    def test_customer_state_filters_return_active_inactive_hidden_and_visible_parties(self):
        entity_model = self.create_entity()
        active_customer = self.create_customer(entity_model, name="API Active Customer")
        inactive_customer = self.create_customer(
            entity_model,
            name="API Inactive Customer",
            active=False,
        )
        hidden_customer = self.create_customer(
            entity_model,
            name="API Hidden Customer",
            hidden=True,
        )
        customer_qs = CustomerModel.objects.for_entity(entity_model)

        self.assert_customer_uuids(customer_qs.active(), [active_customer, hidden_customer])
        self.assert_customer_uuids(customer_qs.inactive(), [inactive_customer])
        self.assert_customer_uuids(customer_qs.hidden(), [hidden_customer])
        self.assert_customer_uuids(customer_qs.visible(), [active_customer])

    def test_vendor_state_filters_return_active_inactive_hidden_and_visible_parties(self):
        entity_model = self.create_entity()
        active_vendor = self.create_vendor(entity_model, name="API Active Vendor")
        inactive_vendor = self.create_vendor(
            entity_model,
            name="API Inactive Vendor",
            active=False,
        )
        hidden_vendor = self.create_vendor(
            entity_model,
            name="API Hidden Vendor",
            hidden=True,
        )
        vendor_qs = VendorModel.objects.for_entity(entity_model)

        self.assert_vendor_uuids(vendor_qs.active(), [active_vendor, hidden_vendor])
        self.assert_vendor_uuids(vendor_qs.inactive(), [inactive_vendor])
        self.assert_vendor_uuids(vendor_qs.hidden(), [hidden_vendor])
        self.assert_vendor_uuids(vendor_qs.visible(), [active_vendor])

    def test_entity_slug_property_uses_queryset_annotation_or_direct_fallback(self):
        entity_model = self.create_entity()
        customer_model = self.create_customer(entity_model)
        vendor_model = self.create_vendor(entity_model)

        annotated_customer = CustomerModel.objects.get(uuid=customer_model.uuid)
        annotated_vendor = VendorModel.objects.get(uuid=vendor_model.uuid)
        direct_customer = CustomerModel(
            customer_name="API Direct Customer",
            entity_model=entity_model,
            description="API Direct Customer description",
        )
        direct_vendor = VendorModel(
            vendor_name="API Direct Vendor",
            entity_model=entity_model,
            description="API Direct Vendor description",
        )

        self.assertEqual(annotated_customer.entity_slug, entity_model.slug)
        self.assertEqual(annotated_vendor.entity_slug, entity_model.slug)
        self.assertEqual(direct_customer.entity_slug, entity_model.slug)
        self.assertEqual(direct_vendor.entity_slug, entity_model.slug)
