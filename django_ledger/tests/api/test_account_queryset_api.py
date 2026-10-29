"""
High-level API behavior tests for AccountModel manager and queryset helpers.

These tests cover entity, chart-of-accounts, and user scoping without relying
on randomized fixtures.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import AccountModel
from django_ledger.models.accounts import AccountModelValidationError
from django_ledger.models.entity import EntityManagementModel, EntityModel


class AccountQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_account_queryset_admin",
            email="api-account-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_account_queryset_other_admin",
            email="api-account-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_account_queryset_manager",
            email="api-account-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_account_queryset_unrelated",
            email="api-account-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_account_queryset_superuser",
            email="api-account-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Account QuerySet Entity", admin=None):
        return EntityModel.create_entity(
            name=name,
            admin=admin or self.admin_user,
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

    def create_cash_account(self, coa_model, *, code, name):
        return coa_model.create_account(
            code=code,
            name=name,
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
        )

    def create_entity_with_two_coas(self, *, name="API Account QuerySet Entity", admin=None):
        entity_model = self.create_entity(name=name, admin=admin)
        default_coa = self.create_coa(
            entity_model,
            name=f"{name} Default CoA",
            assign_as_default=True,
        )
        secondary_coa = self.create_coa(
            entity_model,
            name=f"{name} Secondary CoA",
            assign_as_default=False,
        )
        default_account = self.create_cash_account(
            default_coa,
            code="1010",
            name=f"{name} Default Cash",
        )
        secondary_account = self.create_cash_account(
            secondary_coa,
            code="1010",
            name=f"{name} Secondary Cash",
        )
        return entity_model, default_coa, secondary_coa, default_account, secondary_account

    def test_for_entity_accepts_model_slug_and_uuid(self):
        (
            entity_model,
            _default_coa,
            _secondary_coa,
            account_model,
            _secondary_account,
        ) = self.create_entity_with_two_coas(name="API Account For Entity A")
        (
            _other_entity,
            _other_default_coa,
            _other_secondary_coa,
            other_account,
            _other_secondary_account,
        ) = self.create_entity_with_two_coas(
            name="API Account For Entity B",
            admin=self.other_admin_user,
        )

        for entity_lookup in (entity_model, entity_model.slug, entity_model.uuid):
            with self.subTest(entity_lookup=entity_lookup):
                account_qs = AccountModel.objects.for_entity(entity_lookup)

                self.assertTrue(account_qs.filter(uuid=account_model.uuid).exists())
                self.assertFalse(account_qs.filter(uuid=other_account.uuid).exists())

    def test_for_entity_uses_default_coa_when_no_explicit_coa_is_passed(self):
        (
            entity_model,
            _default_coa,
            _secondary_coa,
            default_account,
            secondary_account,
        ) = self.create_entity_with_two_coas(name="API Account Default CoA Scope")

        account_qs = AccountModel.objects.for_entity(entity_model)

        self.assertTrue(account_qs.filter(uuid=default_account.uuid).exists())
        self.assertFalse(account_qs.filter(uuid=secondary_account.uuid).exists())

    def test_for_entity_accepts_explicit_coa_model_slug_and_uuid(self):
        (
            entity_model,
            _default_coa,
            secondary_coa,
            default_account,
            secondary_account,
        ) = self.create_entity_with_two_coas(name="API Account Explicit CoA Scope")

        for coa_lookup in (secondary_coa, secondary_coa.slug, secondary_coa.uuid):
            with self.subTest(coa_lookup=coa_lookup):
                account_qs = AccountModel.objects.for_entity(
                    entity_model,
                    coa_model=coa_lookup,
                )

                self.assertTrue(account_qs.filter(uuid=secondary_account.uuid).exists())
                self.assertFalse(account_qs.filter(uuid=default_account.uuid).exists())

    def test_for_entity_rejects_invalid_entity_input(self):
        with self.assertRaises(AccountModelValidationError):
            AccountModel.objects.for_entity(object())

    def test_for_entity_rejects_invalid_coa_input(self):
        entity_model = self.create_entity(name="API Account Invalid CoA Entity")

        with self.assertRaises(AccountModelValidationError):
            AccountModel.objects.for_entity(entity_model, coa_model=object())

    def test_for_user_scopes_accounts_by_entity_access(self):
        (
            entity_model,
            _default_coa,
            _secondary_coa,
            account_model,
            _secondary_account,
        ) = self.create_entity_with_two_coas(name="API Account User Scope Entity")
        (
            _other_entity,
            _other_default_coa,
            _other_secondary_coa,
            other_account,
            _other_secondary_account,
        ) = self.create_entity_with_two_coas(
            name="API Account Other User Scope Entity",
            admin=self.other_admin_user,
        )

        EntityManagementModel.objects.create(
            entity=entity_model,
            user=self.manager_user,
            permission_level="read",
        )

        admin_qs = AccountModel.objects.for_user(self.admin_user)
        manager_qs = AccountModel.objects.for_user(self.manager_user)
        unrelated_qs = AccountModel.objects.for_user(self.unrelated_user)
        superuser_qs = AccountModel.objects.for_user(self.superuser)

        self.assertTrue(admin_qs.filter(uuid=account_model.uuid).exists())
        self.assertFalse(admin_qs.filter(uuid=other_account.uuid).exists())

        self.assertTrue(manager_qs.filter(uuid=account_model.uuid).exists())
        self.assertFalse(manager_qs.filter(uuid=other_account.uuid).exists())

        self.assertFalse(unrelated_qs.filter(uuid=account_model.uuid).exists())
        self.assertFalse(unrelated_qs.filter(uuid=other_account.uuid).exists())

        self.assertTrue(superuser_qs.filter(uuid=account_model.uuid).exists())
        self.assertTrue(superuser_qs.filter(uuid=other_account.uuid).exists())
