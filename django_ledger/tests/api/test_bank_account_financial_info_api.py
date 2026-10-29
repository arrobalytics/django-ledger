"""
High-level API behavior tests for BankAccountModel financial account helpers.

These tests cover public helpers inherited from FinancialAccountInfoMixin
without exercising import or reconciliation flows.
"""

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from django_ledger.models import BankAccountModel


class BankAccountFinancialInfoAPITest(SimpleTestCase):
    def test_get_account_last_digits_masks_default_and_custom_lengths(self):
        bank_account = BankAccountModel(account_number="000123456789")

        self.assertEqual(bank_account.get_account_last_digits(), "*6789")
        self.assertEqual(bank_account.get_account_last_digits(n=6), "*456789")

    def test_get_account_last_digits_returns_fallback_when_missing(self):
        bank_account = BankAccountModel(account_number="")

        self.assertEqual(bank_account.get_account_last_digits(), "Not Available")

    def test_get_routing_last_digits_masks_default_and_custom_lengths(self):
        bank_account = BankAccountModel(routing_number="000111222")

        self.assertEqual(bank_account.get_routing_last_digits(), "*1222")
        self.assertEqual(bank_account.get_routing_last_digits(n=6), "*111222")

    def test_get_routing_last_digits_returns_fallback_when_missing(self):
        bank_account = BankAccountModel(routing_number=None)

        self.assertEqual(bank_account.get_routing_last_digits(), "Not Available")

    def test_get_account_type_from_ofx_maps_known_and_unknown_types(self):
        bank_account = BankAccountModel()

        ofx_cases = (
            ("CHECKING", BankAccountModel.ACCOUNT_CHECKING),
            ("SAVINGS", BankAccountModel.ACCOUNT_SAVINGS),
            ("CREDITLINE", BankAccountModel.ACCOUNT_CREDIT_CARD),
            ("CD", BankAccountModel.ACCOUNT_CERT_DEPOSIT),
            ("NOT_A_REAL_OFX_TYPE", BankAccountModel.ACCOUNT_OTHER),
        )

        for ofx_type, expected_account_type in ofx_cases:
            with self.subTest(ofx_type=ofx_type):
                self.assertEqual(
                    bank_account.get_account_type_from_ofx(ofx_type),
                    expected_account_type,
                )


class BankAccountFinancialInfoValidationAPITest(TestCase):
    def test_non_digit_account_number_fails_model_validation(self):
        bank_account = BankAccountModel(account_number="12-34")

        with self.assertRaises(ValidationError):
            bank_account.full_clean(exclude=["entity_model", "account_model"])

    def test_non_digit_routing_number_fails_model_validation(self):
        bank_account = BankAccountModel(routing_number="routing-123")

        with self.assertRaises(ValidationError):
            bank_account.full_clean(exclude=["entity_model", "account_model"])
