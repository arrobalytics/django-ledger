"""
High-level API tests for EntityModel bank account mapping behavior.

These tests cover small user-visible BankAccountModel behaviors that sit at
the EntityModel.create_bank_account() boundary.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, CREDIT, DEBIT, LIABILITY_CL_ACC_PAYABLE
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.entity import EntityModel


class BankAccountEntityMappingAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_bank_account_entity_mapping_admin",
            email="api-bank-account-entity-mapping-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Bank Account Entity Mapping Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_coa(self, entity_model, *, name, assign_as_default=False):
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=name,
            commit=True,
            assign_as_default=assign_as_default,
        )
        entity_model.refresh_from_db()
        return coa_model

    def create_default_account(self, coa_model, *, code, role, balance_type, name):
        return coa_model.create_account(
            code=code,
            name=name,
            role=role,
            balance_type=balance_type,
            active=True,
            is_role_default=True,
        )

    def create_entity_with_default_cash_account(
        self,
        *,
        name="API Bank Account Entity Mapping Cash Entity",
    ):
        entity_model = self.create_entity(name=name)
        coa_model = self.create_coa(
            entity_model,
            name=f"{name} CoA",
            assign_as_default=True,
        )
        cash_account = self.create_default_account(
            coa_model,
            code="1010",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            name=f"{name} Cash",
        )
        return entity_model, coa_model, cash_account

    def test_str_includes_account_type_display_and_name(self):
        entity_model, _coa_model, _cash_account = self.create_entity_with_default_cash_account(
            name="API Bank Account String Entity",
        )
        bank_account = entity_model.create_bank_account(
            name="API Readable Bank Account",
            account_type=BankAccountModel.ACCOUNT_CHECKING,
            active=True,
            bank_account_model_kwargs={
                "account_number": "000000001",
                "routing_number": "000000101",
            },
        )

        display_value = str(bank_account)

        self.assertIsInstance(display_value, str)
        self.assertTrue(display_value)
        self.assertIn("Checking", display_value)
        self.assertIn("Bank Account", display_value)
        self.assertIn("API Readable Bank Account", display_value)

    def test_entity_create_bank_account_commit_false_does_not_persist(self):
        entity_model, _coa_model, cash_account = self.create_entity_with_default_cash_account(
            name="API Bank Account Commit False Entity",
        )
        bank_account_count = BankAccountModel.objects.count()

        bank_account = entity_model.create_bank_account(
            name="API Unsaved Bank Account",
            account_type=BankAccountModel.ACCOUNT_CHECKING,
            active=True,
            bank_account_model_kwargs={
                "account_number": "000000002",
                "routing_number": "000000102",
            },
            commit=False,
        )

        self.assertEqual(bank_account.entity_model_id, entity_model.uuid)
        self.assertEqual(bank_account.account_model_id, cash_account.uuid)
        self.assertTrue(bank_account.active)
        self.assertEqual(BankAccountModel.objects.count(), bank_account_count)
        self.assertFalse(BankAccountModel.objects.filter(uuid=bank_account.uuid).exists())

    def test_entity_create_bank_account_maps_credit_card_to_default_liability_account(self):
        entity_model = self.create_entity(name="API Credit Card Mapping Entity")
        coa_model = self.create_coa(
            entity_model,
            name="API Credit Card Mapping CoA",
            assign_as_default=True,
        )
        payable_account = self.create_default_account(
            coa_model,
            code="2010",
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type=CREDIT,
            name="API Credit Card Payable",
        )

        bank_account = entity_model.create_bank_account(
            name="API Credit Card Account",
            account_type=BankAccountModel.ACCOUNT_CREDIT_CARD,
            active=True,
            bank_account_model_kwargs={
                "account_number": "000000003",
                "routing_number": "000000103",
            },
        )

        self.assertEqual(bank_account.account_model_id, payable_account.uuid)
        self.assertEqual(bank_account.account_model.role, LIABILITY_CL_ACC_PAYABLE)
        self.assertTrue(bank_account.account_model.role_default)

    def test_entity_create_bank_account_uses_explicit_coa_for_default_account_selection(self):
        entity_model = self.create_entity(name="API Bank Account Explicit CoA Entity")
        default_coa = self.create_coa(
            entity_model,
            name="API Bank Account Default CoA",
            assign_as_default=True,
        )
        secondary_coa = self.create_coa(
            entity_model,
            name="API Bank Account Secondary CoA",
            assign_as_default=False,
        )
        default_cash_account = self.create_default_account(
            default_coa,
            code="1010",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            name="API Default CoA Cash",
        )
        secondary_cash_account = self.create_default_account(
            secondary_coa,
            code="1010",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            name="API Secondary CoA Cash",
        )

        bank_account = entity_model.create_bank_account(
            name="API Explicit CoA Bank Account",
            account_type=BankAccountModel.ACCOUNT_CHECKING,
            active=True,
            coa_model=secondary_coa.slug,
            bank_account_model_kwargs={
                "account_number": "000000004",
                "routing_number": "000000104",
            },
        )

        self.assertEqual(bank_account.account_model_id, secondary_cash_account.uuid)
        self.assertNotEqual(bank_account.account_model_id, default_cash_account.uuid)
        self.assertEqual(bank_account.account_model.coa_model_id, secondary_coa.uuid)
