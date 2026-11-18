"""
High-level API tests for CustomerModel and VendorModel numbering behavior.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.vendor import VendorModel
from django_ledger.settings import (
    DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX,
    DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING,
    DJANGO_LEDGER_VENDOR_NUMBER_PREFIX,
)


class CustomerVendorNumberingAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_customer_vendor_numbering_admin",
            email="api-customer-vendor-numbering-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Customer Vendor Numbering Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def make_customer(self, entity_model, *, name="API Numbering Customer"):
        return CustomerModel(
            customer_name=name,
            entity_model=entity_model,
            description=f"{name} description",
        )

    def make_vendor(self, entity_model, *, name="API Numbering Vendor"):
        return VendorModel(
            vendor_name=name,
            entity_model=entity_model,
            description=f"{name} description",
        )

    def create_customer(self, entity_model, *, name="API Numbering Customer"):
        customer_model = self.make_customer(entity_model, name=name)
        customer_model.full_clean()
        customer_model.save()
        return customer_model

    def create_vendor(self, entity_model, *, name="API Numbering Vendor"):
        vendor_model = self.make_vendor(entity_model, name=name)
        vendor_model.full_clean()
        vendor_model.save()
        return vendor_model

    def assert_number_shape(self, number, prefix):
        self.assertTrue(number)
        self.assertTrue(number.startswith(f"{prefix}-"))
        suffix = number.rsplit("-", maxsplit=1)[-1]
        self.assertEqual(len(suffix), DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING)
        self.assertTrue(suffix.isdigit())

    def assert_number_sequence(self, number, sequence):
        self.assertTrue(
            number.endswith(str(sequence).zfill(DJANGO_LEDGER_DOCUMENT_NUMBER_PADDING))
        )

    def get_number_sequence(self, number):
        return int(number.rsplit("-", maxsplit=1)[-1])

    def test_customer_generate_commit_false_sets_number_in_memory_without_saving(self):
        entity_model = self.create_entity()
        customer_model = self.make_customer(entity_model)

        self.assertTrue(customer_model.can_generate_customer_number())

        generated_number = customer_model.generate_customer_number(commit=False)

        self.assertEqual(customer_model.customer_number, generated_number)
        self.assert_number_shape(generated_number, DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX)
        self.assertFalse(CustomerModel.objects.filter(uuid=customer_model.uuid).exists())
        self.assertFalse(customer_model.can_generate_customer_number())

        next_customer = self.create_customer(entity_model, name="API Next Numbering Customer")
        self.assertEqual(
            self.get_number_sequence(next_customer.customer_number),
            self.get_number_sequence(generated_number) + 1,
        )

    def test_vendor_generate_commit_false_sets_number_in_memory_without_saving(self):
        entity_model = self.create_entity()
        vendor_model = self.make_vendor(entity_model)

        self.assertTrue(vendor_model.can_generate_vendor_number())

        generated_number = vendor_model.generate_vendor_number(commit=False)

        self.assertEqual(vendor_model.vendor_number, generated_number)
        self.assert_number_shape(generated_number, DJANGO_LEDGER_VENDOR_NUMBER_PREFIX)
        self.assertFalse(VendorModel.objects.filter(uuid=vendor_model.uuid).exists())
        self.assertFalse(vendor_model.can_generate_vendor_number())

        next_vendor = self.create_vendor(entity_model, name="API Next Numbering Vendor")
        self.assertEqual(
            self.get_number_sequence(next_vendor.vendor_number),
            self.get_number_sequence(generated_number) + 1,
        )

    def test_customer_generate_commit_true_persists_number_for_saved_customer(self):
        entity_model = self.create_entity()
        customer_model = self.create_customer(entity_model)
        CustomerModel.objects.filter(uuid=customer_model.uuid).update(customer_number="")
        customer_model.customer_number = ""

        self.assertTrue(customer_model.can_generate_customer_number())

        generated_number = customer_model.generate_customer_number(commit=True)

        customer_model.refresh_from_db()
        self.assertEqual(customer_model.customer_number, generated_number)
        self.assert_number_shape(generated_number, DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX)

    def test_vendor_generate_commit_true_persists_number_for_saved_vendor(self):
        entity_model = self.create_entity()
        vendor_model = self.create_vendor(entity_model)
        VendorModel.objects.filter(uuid=vendor_model.uuid).update(vendor_number=None)
        vendor_model.vendor_number = None

        self.assertTrue(vendor_model.can_generate_vendor_number())

        generated_number = vendor_model.generate_vendor_number(commit=True)

        vendor_model.refresh_from_db()
        self.assertEqual(vendor_model.vendor_number, generated_number)
        self.assert_number_shape(generated_number, DJANGO_LEDGER_VENDOR_NUMBER_PREFIX)

    def test_clean_and_save_generate_numbers_for_customer_and_vendor(self):
        entity_model = self.create_entity()
        customer_model = self.make_customer(entity_model)
        vendor_model = self.make_vendor(entity_model)

        customer_model.clean()
        vendor_model.clean()

        self.assert_number_shape(
            customer_model.customer_number,
            DJANGO_LEDGER_CUSTOMER_NUMBER_PREFIX,
        )
        self.assert_number_shape(
            vendor_model.vendor_number,
            DJANGO_LEDGER_VENDOR_NUMBER_PREFIX,
        )
        self.assertFalse(CustomerModel.objects.filter(uuid=customer_model.uuid).exists())
        self.assertFalse(VendorModel.objects.filter(uuid=vendor_model.uuid).exists())

        customer_number = customer_model.customer_number
        vendor_number = vendor_model.vendor_number
        customer_model.save()
        vendor_model.save()

        customer_model.refresh_from_db()
        vendor_model.refresh_from_db()
        self.assertEqual(customer_model.customer_number, customer_number)
        self.assertEqual(vendor_model.vendor_number, vendor_number)

    def test_customer_and_vendor_sequences_are_entity_scoped(self):
        entity_a = self.create_entity(name="API Numbering Entity A")
        entity_b = self.create_entity(name="API Numbering Entity B")

        customer_a1 = self.create_customer(entity_a, name="API Entity A Customer 1")
        customer_a2 = self.create_customer(entity_a, name="API Entity A Customer 2")
        customer_b1 = self.create_customer(entity_b, name="API Entity B Customer 1")
        vendor_a1 = self.create_vendor(entity_a, name="API Entity A Vendor 1")
        vendor_a2 = self.create_vendor(entity_a, name="API Entity A Vendor 2")
        vendor_b1 = self.create_vendor(entity_b, name="API Entity B Vendor 1")

        self.assert_number_sequence(customer_a1.customer_number, 1)
        self.assert_number_sequence(customer_a2.customer_number, 2)
        self.assert_number_sequence(customer_b1.customer_number, 1)
        self.assert_number_sequence(vendor_a1.vendor_number, 1)
        self.assert_number_sequence(vendor_a2.vendor_number, 2)
        self.assert_number_sequence(vendor_b1.vendor_number, 1)

    def test_existing_customer_number_prevents_regeneration(self):
        customer_model = self.create_customer(self.create_entity())
        original_number = customer_model.customer_number

        self.assertFalse(customer_model.can_generate_customer_number())

        generated_number = customer_model.generate_customer_number(commit=False)

        self.assertEqual(generated_number, original_number)
        self.assertEqual(customer_model.customer_number, original_number)

    def test_existing_vendor_number_prevents_regeneration(self):
        vendor_model = self.create_vendor(self.create_entity())
        original_number = vendor_model.vendor_number

        self.assertFalse(vendor_model.can_generate_vendor_number())

        generated_number = vendor_model.generate_vendor_number(commit=False)

        self.assertEqual(generated_number, original_number)
        self.assertEqual(vendor_model.vendor_number, original_number)
