"""
High-level API behavior tests for EntityModel bank account wrappers.

These tests cover entity-scoped bank account creation, default account
selection, explicit account selection, and active filtering.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.entity import EntityModel, EntityModelValidationError


class EntityBankAccountAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_entity_bank_account_admin",
            email="api-entity-bank-account-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_entity_bank_account_other_admin",
            email="api-entity-bank-account-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_with_bank_account_setup(
        self,
        *,
        name="API Entity Bank Account Entity",
        admin=None,
    ):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=admin or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        cash_role = BankAccountModel.ACCOUNT_TYPE_DEFAULT_ROLE_MAPPING[
            BankAccountModel.ACCOUNT_CHECKING
        ]
        default_cash_account = entity_model.create_account(
            code="1010",
            role=cash_role,
            name=f"{name} Default Cash",
            balance_type="debit",
            active=True,
            coa_model=coa_model,
            is_role_default=True,
        )
        explicit_cash_account = entity_model.create_account(
            code="1020",
            role=cash_role,
            name=f"{name} Explicit Cash",
            balance_type="debit",
            active=True,
            coa_model=coa_model,
        )

        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "default_cash_account": default_cash_account,
            "explicit_cash_account": explicit_cash_account,
        }

    def create_bank_account(
        self,
        entity_model,
        *,
        name="API Entity Bank Account",
        account_number="000000001",
        routing_number="000000101",
        active=True,
        account_model=None,
    ):
        return entity_model.create_bank_account(
            name=name,
            account_type=BankAccountModel.ACCOUNT_CHECKING,
            active=active,
            account_model=account_model,
            bank_account_model_kwargs={
                "account_number": account_number,
                "routing_number": routing_number,
            },
        )

    def test_create_bank_account_creates_account_under_entity(self):
        setup = self.create_entity_with_bank_account_setup()
        entity_model = setup["entity_model"]

        bank_account = self.create_bank_account(entity_model)

        self.assertIsInstance(bank_account, BankAccountModel)
        self.assertEqual(bank_account.entity_model_id, entity_model.uuid)
        self.assertEqual(bank_account.name, "API Entity Bank Account")
        self.assertEqual(bank_account.account_type, BankAccountModel.ACCOUNT_CHECKING)
        self.assertEqual(bank_account.account_number, "000000001")
        self.assertEqual(bank_account.routing_number, "000000101")
        self.assertTrue(bank_account.active)

    def test_create_bank_account_uses_default_account_for_account_type(self):
        setup = self.create_entity_with_bank_account_setup()
        entity_model = setup["entity_model"]

        bank_account = self.create_bank_account(entity_model)

        self.assertEqual(
            bank_account.account_model_id,
            setup["default_cash_account"].uuid,
        )

    def test_create_bank_account_respects_explicit_account_model(self):
        setup = self.create_entity_with_bank_account_setup()
        entity_model = setup["entity_model"]

        bank_account = self.create_bank_account(
            entity_model,
            account_model=setup["explicit_cash_account"],
        )

        self.assertEqual(
            bank_account.account_model_id,
            setup["explicit_cash_account"].uuid,
        )

    def test_create_bank_account_rejects_cross_entity_explicit_account_model_without_side_effect(self):
        setup = self.create_entity_with_bank_account_setup(
            name="API Bank Account Explicit Account Entity"
        )
        other_setup = self.create_entity_with_bank_account_setup(
            name="API Other Bank Account Explicit Account Entity",
            admin=self.other_admin_user,
        )
        bank_account_count = BankAccountModel.objects.count()

        with self.assertRaises(EntityModelValidationError):
            self.create_bank_account(
                setup["entity_model"],
                name="API Cross Entity Explicit Account Bank Account",
                account_number="000000099",
                routing_number="000000199",
                account_model=other_setup["explicit_cash_account"],
            )

        self.assertEqual(BankAccountModel.objects.count(), bank_account_count)
        self.assertFalse(
            setup["entity_model"]
            .get_bank_accounts(active=False)
            .filter(name="API Cross Entity Explicit Account Bank Account")
            .exists()
        )

    def test_create_bank_account_rejects_invalid_account_type(self):
        setup = self.create_entity_with_bank_account_setup()

        with self.assertRaises(EntityModelValidationError):
            setup["entity_model"].create_bank_account(
                name="API Invalid Bank Account",
                account_type="not-a-bank-account-type",
                active=True,
                bank_account_model_kwargs={
                    "account_number": "000000001",
                    "routing_number": "000000101",
                },
            )

    def test_get_bank_accounts_is_entity_scoped_and_filters_inactive_by_default(self):
        setup = self.create_entity_with_bank_account_setup(
            name="API Bank Account Scoped Entity"
        )
        other_setup = self.create_entity_with_bank_account_setup(
            name="API Other Bank Account Scoped Entity",
            admin=self.other_admin_user,
        )
        entity_model = setup["entity_model"]
        other_entity = other_setup["entity_model"]

        active_bank_account = self.create_bank_account(
            entity_model,
            name="API Active Entity Bank Account",
            account_number="000000001",
            routing_number="000000101",
            active=True,
        )
        inactive_bank_account = self.create_bank_account(
            entity_model,
            name="API Inactive Entity Bank Account",
            account_number="000000002",
            routing_number="000000102",
            active=False,
        )
        other_bank_account = self.create_bank_account(
            other_entity,
            name="API Other Entity Bank Account",
            account_number="000000001",
            routing_number="000000101",
            active=True,
        )

        default_bank_account_qs = entity_model.get_bank_accounts()
        all_bank_account_qs = entity_model.get_bank_accounts(active=False)

        self.assertTrue(
            default_bank_account_qs.filter(uuid=active_bank_account.uuid).exists()
        )
        self.assertFalse(
            default_bank_account_qs.filter(uuid=inactive_bank_account.uuid).exists()
        )
        self.assertFalse(
            default_bank_account_qs.filter(uuid=other_bank_account.uuid).exists()
        )

        self.assertTrue(
            all_bank_account_qs.filter(uuid=active_bank_account.uuid).exists()
        )
        self.assertTrue(
            all_bank_account_qs.filter(uuid=inactive_bank_account.uuid).exists()
        )
        self.assertFalse(
            all_bank_account_qs.filter(uuid=other_bank_account.uuid).exists()
        )
