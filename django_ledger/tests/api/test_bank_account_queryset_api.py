"""
High-level API behavior tests for BankAccountModel queryset helpers.

These tests cover entity/user scoping and simple public queryset filters
without exercising data import or staged transaction behavior.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT
from django_ledger.models import BankAccountModel
from django_ledger.models.bank_account import BankAccountValidationError
from django_ledger.models.entity import EntityManagementModel, EntityModel


class BankAccountQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_bank_account_queryset_admin",
            email="api-bank-account-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_bank_account_queryset_other_admin",
            email="api-bank-account-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_bank_account_queryset_manager",
            email="api-bank-account-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_bank_account_queryset_unrelated",
            email="api-bank-account-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_bank_account_queryset_superuser",
            email="api-bank-account-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Bank Account QuerySet Entity", admin=None):
        return EntityModel.create_entity(
            name=name,
            admin=admin or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_entity_setup(
        self,
        *,
        name="API Bank Account QuerySet Entity",
        admin=None,
    ):
        entity_model = self.create_entity(name=name, admin=admin)
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        cash_account = coa_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        return {
            "entity_model": entity_model,
            "coa_model": coa_model,
            "cash_account": cash_account,
        }

    def create_bank_account(
        self,
        setup,
        *,
        name="API Bank Account QuerySet Account",
        account_number="000123456789",
        routing_number="000111000",
        active=True,
        hidden=False,
    ):
        bank_account = BankAccountModel(
            name=name,
            account_model=setup["cash_account"],
            account_number=account_number,
            routing_number=routing_number,
            active=active,
            hidden=hidden,
        )
        bank_account.configure(
            entity_slug=setup["entity_model"],
            user_model=self.admin_user,
            commit=True,
        )
        bank_account.refresh_from_db()
        return bank_account

    def test_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API Bank Account For Entity A")
        other_setup = self.create_entity_setup(
            name="API Bank Account For Entity B",
            admin=self.other_admin_user,
        )
        bank_account = self.create_bank_account(
            setup,
            account_number="000123456789",
            routing_number="000111000",
        )
        other_bank_account = self.create_bank_account(
            other_setup,
            account_number="000123456789",
            routing_number="000111000",
        )
        entity_model = setup["entity_model"]

        for entity_lookup in (entity_model, entity_model.slug, entity_model.uuid):
            with self.subTest(entity_lookup=entity_lookup):
                bank_account_qs = BankAccountModel.objects.for_entity(entity_lookup)

                self.assertTrue(bank_account_qs.filter(uuid=bank_account.uuid).exists())
                self.assertFalse(
                    bank_account_qs.filter(uuid=other_bank_account.uuid).exists()
                )

    def test_for_entity_rejects_invalid_input(self):
        with self.assertRaises(BankAccountValidationError):
            BankAccountModel.objects.for_entity(object())

    def test_for_user_scopes_bank_accounts_by_entity_access(self):
        setup = self.create_entity_setup(name="API Bank Account User Scope Entity")
        other_setup = self.create_entity_setup(
            name="API Bank Account Other User Scope Entity",
            admin=self.other_admin_user,
        )
        bank_account = self.create_bank_account(
            setup,
            account_number="000123456789",
            routing_number="000111000",
        )
        other_bank_account = self.create_bank_account(
            other_setup,
            account_number="000123456789",
            routing_number="000111000",
        )

        EntityManagementModel.objects.create(
            entity=setup["entity_model"],
            user=self.manager_user,
            permission_level="read",
        )

        bank_account_qs = BankAccountModel.objects.all()
        admin_qs = bank_account_qs.for_user(self.admin_user)
        manager_qs = bank_account_qs.for_user(self.manager_user)
        unrelated_qs = bank_account_qs.for_user(self.unrelated_user)
        superuser_qs = bank_account_qs.for_user(self.superuser)

        self.assertTrue(admin_qs.filter(uuid=bank_account.uuid).exists())
        self.assertFalse(admin_qs.filter(uuid=other_bank_account.uuid).exists())

        self.assertTrue(manager_qs.filter(uuid=bank_account.uuid).exists())
        self.assertFalse(manager_qs.filter(uuid=other_bank_account.uuid).exists())

        self.assertFalse(unrelated_qs.filter(uuid=bank_account.uuid).exists())
        self.assertFalse(unrelated_qs.filter(uuid=other_bank_account.uuid).exists())

        self.assertTrue(superuser_qs.filter(uuid=bank_account.uuid).exists())
        self.assertTrue(superuser_qs.filter(uuid=other_bank_account.uuid).exists())

    def test_active_and_hidden_filters_return_matching_bank_accounts(self):
        setup = self.create_entity_setup(name="API Bank Account Filter Entity")
        active_bank_account = self.create_bank_account(
            setup,
            name="API Active Bank Account",
            account_number="000123456789",
            routing_number="000111000",
            active=True,
            hidden=False,
        )
        inactive_bank_account = self.create_bank_account(
            setup,
            name="API Inactive Bank Account",
            account_number="000987654321",
            routing_number="000222000",
            active=False,
            hidden=False,
        )
        hidden_bank_account = self.create_bank_account(
            setup,
            name="API Hidden Bank Account",
            account_number="000555555555",
            routing_number="000333000",
            active=True,
            hidden=True,
        )

        bank_account_qs = BankAccountModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(
            bank_account_qs.active().filter(uuid=active_bank_account.uuid).exists()
        )
        self.assertTrue(
            bank_account_qs.active().filter(uuid=hidden_bank_account.uuid).exists()
        )
        self.assertFalse(
            bank_account_qs.active().filter(uuid=inactive_bank_account.uuid).exists()
        )

        self.assertTrue(
            bank_account_qs.hidden().filter(uuid=hidden_bank_account.uuid).exists()
        )
        self.assertFalse(
            bank_account_qs.hidden().filter(uuid=active_bank_account.uuid).exists()
        )

    def test_configure_with_entity_slug_and_authorized_user_binds_entity(self):
        setup = self.create_entity_setup(name="API Bank Account Configure Slug Entity")
        bank_account = BankAccountModel(
            name="API Slug Configured Bank Account",
            account_model=setup["cash_account"],
            account_number="000123456789",
            routing_number="000111000",
            active=True,
        )

        returned_bank_account, returned_entity = bank_account.configure(
            entity_slug=setup["entity_model"].slug,
            user_model=self.admin_user,
            commit=True,
        )

        returned_bank_account.refresh_from_db()

        self.assertEqual(returned_bank_account, bank_account)
        self.assertEqual(returned_entity, setup["entity_model"])
        self.assertEqual(bank_account.entity_model_id, setup["entity_model"].uuid)
