"""
High-level API tests for UnitOfMeasureModel manager and queryset behavior.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModelValidationError, UnitOfMeasureModel


class UnitOfMeasureQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_uom_queryset_admin",
            email="api-uom-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_uom_queryset_manager",
            email="api-uom-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_uom_queryset_other_admin",
            email="api-uom-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_uom_queryset_unrelated",
            email="api-uom-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_uom_queryset_superuser",
            email="api-uom-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API UOM Queryset Entity", admin_user=None, manager_user=None):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=admin_user or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        if manager_user is not None:
            entity_model.managers.add(manager_user)
        return entity_model

    def create_uom(self, entity_model, *, name="API Queryset Unit", unit_abbr="api-uom", active=True):
        return entity_model.create_uom(
            name=name,
            unit_abbr=unit_abbr,
            active=active,
            commit=True,
        )

    def assert_uom_uuids(self, queryset, expected_uoms):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {uom_model.uuid for uom_model in expected_uoms},
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        entity_model = self.create_entity(name="API UOM Queryset Entity A")
        other_entity_model = self.create_entity(
            name="API UOM Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        uom_model = self.create_uom(entity_model, unit_abbr="api-uom-a")
        self.create_uom(other_entity_model, unit_abbr="api-uom-b")

        self.assert_uom_uuids(UnitOfMeasureModel.objects.for_entity(entity_model), [uom_model])
        self.assert_uom_uuids(UnitOfMeasureModel.objects.for_entity(entity_model.slug), [uom_model])
        self.assert_uom_uuids(UnitOfMeasureModel.objects.for_entity(entity_model.uuid), [uom_model])

    def test_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_uom(self.create_entity())

        with self.assertRaises(ItemModelValidationError):
            UnitOfMeasureModel.objects.for_entity(object())

        self.assertFalse(UnitOfMeasureModel.objects.for_entity("missing-uom-entity-slug").exists())

    def test_for_entity_active_returns_only_active_units(self):
        entity_model = self.create_entity()
        active_uom = self.create_uom(entity_model, name="API Active Unit", unit_abbr="api-act", active=True)
        inactive_uom = self.create_uom(
            entity_model,
            name="API Inactive Unit",
            unit_abbr="api-inact",
            active=False,
        )

        active_qs = UnitOfMeasureModel.objects.for_entity_active(entity_model)

        self.assertTrue(active_qs.filter(uuid=active_uom.uuid).exists())
        self.assertFalse(active_qs.filter(uuid=inactive_uom.uuid).exists())

    def test_for_user_scopes_to_admin_manager_and_current_superuser_behavior(self):
        entity_model = self.create_entity(
            name="API UOM Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_entity_model = self.create_entity(
            name="API UOM Queryset Other Access Entity",
            admin_user=self.other_admin_user,
        )
        uom_model = self.create_uom(entity_model, unit_abbr="api-acc")
        self.create_uom(other_entity_model, unit_abbr="api-oacc")

        self.assert_uom_uuids(UnitOfMeasureModel.objects.all().for_user(self.admin_user), [uom_model])
        self.assert_uom_uuids(UnitOfMeasureModel.objects.all().for_user(self.manager_user), [uom_model])
        self.assertFalse(UnitOfMeasureModel.objects.all().for_user(self.unrelated_user).exists())
        self.assertFalse(UnitOfMeasureModel.objects.all().for_user(self.superuser).exists())

    def test_str_returns_user_facing_unit_name_and_abbreviation(self):
        uom_model = self.create_uom(
            self.create_entity(),
            name="API Hours",
            unit_abbr="api-hrs",
        )

        display = str(uom_model)

        self.assertTrue(display)
        self.assertIn("API Hours", display)
        self.assertIn("api-hrs", display)
