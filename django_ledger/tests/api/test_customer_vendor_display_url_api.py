"""
High-level API tests for CustomerModel and VendorModel display, URL, and upload helpers.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.customer import CustomerModel, customer_picture_upload_to
from django_ledger.models.entity import EntityModel
from django_ledger.models.vendor import VendorModel, vendor_picture_upload_to


class CustomerVendorDisplayURLAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_customer_vendor_display_admin",
            email="api-customer-vendor-display-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Customer Vendor Display Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_customer(self, entity_model, *, name="API Display Customer"):
        customer_model = CustomerModel(
            customer_name=name,
            entity_model=entity_model,
            description=f"{name} description",
        )
        customer_model.full_clean()
        customer_model.save()
        return customer_model

    def create_vendor(self, entity_model, *, name="API Display Vendor"):
        vendor_model = VendorModel(
            vendor_name=name,
            entity_model=entity_model,
            description=f"{name} description",
        )
        vendor_model.full_clean()
        vendor_model.save()
        return vendor_model

    def assert_entity_and_party_identifiers_in_url(self, url, entity_model, party_model):
        self.assertIsInstance(url, str)
        self.assertIn(entity_model.slug, url)
        self.assertIn(str(party_model.uuid), url)

    def test_customer_and_vendor_str_include_number_and_name(self):
        entity_model = self.create_entity()
        customer_model = self.create_customer(entity_model, name="API String Customer")
        vendor_model = self.create_vendor(entity_model, name="API String Vendor")

        customer_text = str(customer_model)
        vendor_text = str(vendor_model)

        self.assertIn(customer_model.customer_number, customer_text)
        self.assertIn(customer_model.customer_name, customer_text)
        self.assertIn(vendor_model.vendor_number, vendor_text)
        self.assertIn(vendor_model.vendor_name, vendor_text)

    def test_unknown_number_str_still_returns_party_context(self):
        entity_model = self.create_entity()
        customer_model = CustomerModel(
            customer_name="API Unknown Customer",
            entity_model=entity_model,
            description="API Unknown Customer description",
        )
        vendor_model = VendorModel(
            vendor_name="API Unknown Vendor",
            entity_model=entity_model,
            description="API Unknown Vendor description",
        )

        self.assertIn(customer_model.customer_name, str(customer_model))
        self.assertIn(vendor_model.vendor_name, str(vendor_model))

    def test_customer_url_helpers_return_entity_scoped_strings(self):
        entity_model = self.create_entity()
        customer_model = self.create_customer(entity_model)

        absolute_url = customer_model.get_absolute_url()
        detail_url = customer_model.get_detail_url()
        update_url = customer_model.get_update_url()

        self.assertEqual(absolute_url, detail_url)
        self.assert_entity_and_party_identifiers_in_url(absolute_url, entity_model, customer_model)
        self.assert_entity_and_party_identifiers_in_url(update_url, entity_model, customer_model)

    def test_vendor_url_helpers_return_entity_scoped_strings(self):
        entity_model = self.create_entity()
        vendor_model = self.create_vendor(entity_model)

        absolute_url = vendor_model.get_absolute_url()
        detail_url = vendor_model.get_detail_url()
        update_url = vendor_model.get_update_url()

        self.assertEqual(absolute_url, detail_url)
        self.assert_entity_and_party_identifiers_in_url(absolute_url, entity_model, vendor_model)
        self.assert_entity_and_party_identifiers_in_url(update_url, entity_model, vendor_model)

    def test_picture_upload_paths_use_party_number_and_sanitized_extension(self):
        entity_model = self.create_entity()
        customer_model = self.create_customer(entity_model)
        vendor_model = self.create_vendor(entity_model)

        customer_path = customer_picture_upload_to(customer_model, "Customer Logo.PNG")
        vendor_path = vendor_picture_upload_to(vendor_model, "Vendor Logo.PNG")

        self.assertTrue(customer_path.startswith("customer_pictures/"))
        self.assertIn(customer_model.customer_number, customer_path)
        self.assertTrue(customer_path.endswith("/customer-logo.png"))
        self.assertTrue(vendor_path.startswith("vendor_pictures/"))
        self.assertIn(vendor_model.vendor_number, vendor_path)
        self.assertTrue(vendor_path.endswith("/vendor-logo.png"))

    def test_picture_upload_paths_generate_missing_party_numbers_in_memory(self):
        entity_model = self.create_entity()
        customer_model = CustomerModel(
            customer_name="API Upload Customer",
            entity_model=entity_model,
            description="API Upload Customer description",
        )
        vendor_model = VendorModel(
            vendor_name="API Upload Vendor",
            entity_model=entity_model,
            description="API Upload Vendor description",
        )

        customer_path = customer_picture_upload_to(customer_model, "receipt.JPG")
        vendor_path = vendor_picture_upload_to(vendor_model, "bill.JPG")

        self.assertTrue(customer_model.customer_number)
        self.assertTrue(vendor_model.vendor_number)
        self.assertIn(customer_model.customer_number, customer_path)
        self.assertIn(vendor_model.vendor_number, vendor_path)
        self.assertFalse(CustomerModel.objects.filter(uuid=customer_model.uuid).exists())
        self.assertFalse(VendorModel.objects.filter(uuid=vendor_model.uuid).exists())
