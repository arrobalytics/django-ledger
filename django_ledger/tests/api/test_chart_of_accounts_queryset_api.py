"""
High-level API behavior tests for ChartOfAccountModel manager/queryset helpers.

These tests cover entity/user scoping, active filters, and manager annotations
without over-specifying account counts.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT
from django_ledger.models import ChartOfAccountModel
from django_ledger.models.chart_of_accounts import ChartOfAccountsModelValidationError
from django_ledger.models.entity import EntityModel


class ChartOfAccountsQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_coa_queryset_admin",
            email="api-coa-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_coa_queryset_other_admin",
            email="api-coa-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_coa_queryset_unrelated",
            email="api-coa-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_coa_queryset_superuser",
            email="api-coa-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API CoA QuerySet Entity", admin=None):
        return EntityModel.create_entity(
            name=name,
            admin=admin or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_coa(
        self,
        entity_model,
        *,
        name,
        assign_as_default=False,
        active=True,
    ):
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=name,
            commit=True,
            assign_as_default=assign_as_default,
        )
        if coa_model.active != active:
            coa_model.active = active
            coa_model.save(update_fields=["active", "updated"])
        entity_model.refresh_from_db()
        return coa_model

    def test_for_entity_accepts_model_slug_and_uuid(self):
        entity_model = self.create_entity(name="API CoA For Entity A")
        other_entity = self.create_entity(
            name="API CoA For Entity B",
            admin=self.other_admin_user,
        )
        coa_model = self.create_coa(
            entity_model,
            name="API CoA For Entity A CoA",
            assign_as_default=True,
        )
        other_coa = self.create_coa(
            other_entity,
            name="API CoA For Entity B CoA",
            assign_as_default=True,
        )

        for entity_lookup in (entity_model, entity_model.slug, entity_model.uuid):
            with self.subTest(entity_lookup=entity_lookup):
                coa_qs = ChartOfAccountModel.objects.for_entity(entity_lookup)

                self.assertTrue(coa_qs.filter(uuid=coa_model.uuid).exists())
                self.assertFalse(coa_qs.filter(uuid=other_coa.uuid).exists())

    def test_for_entity_rejects_invalid_entity_argument(self):
        with self.assertRaises(ChartOfAccountsModelValidationError):
            ChartOfAccountModel.objects.for_entity(object())

    def test_active_and_not_active_filters_return_matching_coas(self):
        entity_model = self.create_entity(name="API CoA Active Filter Entity")
        active_coa = self.create_coa(
            entity_model,
            name="API CoA Active Filter Active",
            assign_as_default=True,
            active=True,
        )
        inactive_coa = self.create_coa(
            entity_model,
            name="API CoA Active Filter Inactive",
            assign_as_default=False,
            active=False,
        )

        coa_qs = ChartOfAccountModel.objects.for_entity(entity_model)

        self.assertTrue(coa_qs.active().filter(uuid=active_coa.uuid).exists())
        self.assertFalse(coa_qs.active().filter(uuid=inactive_coa.uuid).exists())

        self.assertTrue(coa_qs.not_active().filter(uuid=inactive_coa.uuid).exists())
        self.assertFalse(coa_qs.not_active().filter(uuid=active_coa.uuid).exists())

    def test_for_user_scopes_coas_by_entity_access(self):
        entity_model = self.create_entity(name="API CoA User Scope Entity")
        other_entity = self.create_entity(
            name="API CoA Other User Scope Entity",
            admin=self.other_admin_user,
        )
        coa_model = self.create_coa(
            entity_model,
            name="API CoA User Scope CoA",
            assign_as_default=True,
        )
        other_coa = self.create_coa(
            other_entity,
            name="API CoA Other User Scope CoA",
            assign_as_default=True,
        )

        admin_qs = ChartOfAccountModel.objects.for_user(self.admin_user)
        unrelated_qs = ChartOfAccountModel.objects.for_user(self.unrelated_user)
        superuser_qs = ChartOfAccountModel.objects.for_user(self.superuser)

        self.assertTrue(admin_qs.filter(uuid=coa_model.uuid).exists())
        self.assertFalse(admin_qs.filter(uuid=other_coa.uuid).exists())

        self.assertFalse(unrelated_qs.filter(uuid=coa_model.uuid).exists())
        self.assertFalse(unrelated_qs.filter(uuid=other_coa.uuid).exists())

        self.assertTrue(superuser_qs.filter(uuid=coa_model.uuid).exists())
        self.assertTrue(superuser_qs.filter(uuid=other_coa.uuid).exists())

    def test_manager_queryset_exposes_configuration_annotations(self):
        entity_model = self.create_entity(name="API CoA Annotation Entity")
        coa_model = self.create_coa(
            entity_model,
            name="API CoA Annotation CoA",
            assign_as_default=True,
        )
        coa_model.create_account(
            code="1010",
            name="API Cash Account",
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
        )

        annotated_coa = ChartOfAccountModel.objects.get(uuid=coa_model.uuid)

        self.assertEqual(annotated_coa._entity_slug, entity_model.slug)
        self.assertTrue(annotated_coa.configured)

        for annotation_name in (
            "accountmodel_total__count",
            "accountmodel_active__count",
            "accountmodel_locked__count",
            "accountmodel_rootgroup__count",
            "accountmodel_rootgroup_roles__distinct_count",
        ):
            with self.subTest(annotation_name=annotation_name):
                self.assertTrue(hasattr(annotated_coa, annotation_name))
                self.assertIsInstance(getattr(annotated_coa, annotation_name), int)
