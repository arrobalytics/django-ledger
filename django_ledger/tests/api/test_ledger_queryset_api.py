"""
High-level API behavior tests for LedgerModel manager and queryset helpers.

These tests cover entity/user scoping, public queryset filters, and entity slug
access without requiring accounting fixtures.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import LedgerModel
from django_ledger.models.entity import EntityManagementModel, EntityModel
from django_ledger.models.ledger import LedgerModelValidationError


class LedgerQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_ledger_queryset_admin",
            email="api-ledger-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_ledger_queryset_other_admin",
            email="api-ledger-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_ledger_queryset_manager",
            email="api-ledger-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_ledger_queryset_unrelated",
            email="api-ledger-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_ledger_queryset_superuser",
            email="api-ledger-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Ledger QuerySet Entity", admin=None):
        return EntityModel.create_entity(
            name=name,
            admin=admin or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_ledger(
        self,
        entity_model,
        *,
        name="API Ledger QuerySet Ledger",
        ledger_xid="api-ledger-queryset-ledger",
        posted=False,
        locked=False,
        hidden=False,
    ):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=ledger_xid,
            entity=entity_model,
            posted=posted,
            locked=locked,
            hidden=hidden,
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        entity_model = self.create_entity(name="API Ledger For Entity A")
        other_entity = self.create_entity(
            name="API Ledger For Entity B",
            admin=self.other_admin_user,
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-for-entity-a",
        )
        other_ledger = self.create_ledger(
            other_entity,
            ledger_xid="api-ledger-for-entity-b",
        )

        for entity_lookup in (entity_model, entity_model.slug, entity_model.uuid):
            with self.subTest(entity_lookup=entity_lookup):
                ledger_qs = LedgerModel.objects.for_entity(entity_lookup)

                self.assertTrue(ledger_qs.filter(uuid=ledger_model.uuid).exists())
                self.assertFalse(ledger_qs.filter(uuid=other_ledger.uuid).exists())

    def test_for_entity_rejects_invalid_input(self):
        with self.assertRaises(LedgerModelValidationError):
            LedgerModel.objects.for_entity(object())

    def test_for_user_scopes_ledgers_by_entity_access(self):
        entity_model = self.create_entity(name="API Ledger User Scope Entity")
        other_entity = self.create_entity(
            name="API Ledger Other User Scope Entity",
            admin=self.other_admin_user,
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-user-scope",
        )
        other_ledger = self.create_ledger(
            other_entity,
            ledger_xid="api-ledger-other-user-scope",
        )

        EntityManagementModel.objects.create(
            entity=entity_model,
            user=self.manager_user,
            permission_level="read",
        )

        admin_qs = LedgerModel.objects.for_user(self.admin_user)
        manager_qs = LedgerModel.objects.for_user(self.manager_user)
        unrelated_qs = LedgerModel.objects.for_user(self.unrelated_user)
        superuser_qs = LedgerModel.objects.for_user(self.superuser)

        self.assertTrue(admin_qs.filter(uuid=ledger_model.uuid).exists())
        self.assertFalse(admin_qs.filter(uuid=other_ledger.uuid).exists())

        self.assertTrue(manager_qs.filter(uuid=ledger_model.uuid).exists())
        self.assertFalse(manager_qs.filter(uuid=other_ledger.uuid).exists())

        self.assertFalse(unrelated_qs.filter(uuid=ledger_model.uuid).exists())
        self.assertFalse(unrelated_qs.filter(uuid=other_ledger.uuid).exists())

        self.assertTrue(superuser_qs.filter(uuid=ledger_model.uuid).exists())
        self.assertTrue(superuser_qs.filter(uuid=other_ledger.uuid).exists())

    def test_queryset_filters_return_matching_ledgers(self):
        entity_model = self.create_entity(name="API Ledger Filter Entity")
        locked_ledger = self.create_ledger(
            entity_model,
            name="API Locked Ledger",
            ledger_xid="api-locked-ledger",
            locked=True,
        )
        unlocked_ledger = self.create_ledger(
            entity_model,
            name="API Unlocked Ledger",
            ledger_xid="api-unlocked-ledger",
            locked=False,
        )
        posted_ledger = self.create_ledger(
            entity_model,
            name="API Posted Ledger",
            ledger_xid="api-posted-ledger",
            posted=True,
        )
        hidden_ledger = self.create_ledger(
            entity_model,
            name="API Hidden Ledger",
            ledger_xid="api-hidden-ledger",
            hidden=True,
        )
        visible_ledger = self.create_ledger(
            entity_model,
            name="API Visible Ledger",
            ledger_xid="api-visible-ledger",
            hidden=False,
        )

        ledger_qs = LedgerModel.objects.for_entity(entity_model)

        self.assertTrue(ledger_qs.locked().filter(uuid=locked_ledger.uuid).exists())
        self.assertFalse(ledger_qs.locked().filter(uuid=unlocked_ledger.uuid).exists())

        self.assertTrue(ledger_qs.unlocked().filter(uuid=unlocked_ledger.uuid).exists())
        self.assertFalse(ledger_qs.unlocked().filter(uuid=locked_ledger.uuid).exists())

        self.assertTrue(ledger_qs.posted().filter(uuid=posted_ledger.uuid).exists())
        self.assertFalse(ledger_qs.posted().filter(uuid=unlocked_ledger.uuid).exists())

        self.assertTrue(ledger_qs.hidden().filter(uuid=hidden_ledger.uuid).exists())
        self.assertFalse(ledger_qs.hidden().filter(uuid=visible_ledger.uuid).exists())

        self.assertTrue(ledger_qs.visible().filter(uuid=visible_ledger.uuid).exists())
        self.assertFalse(ledger_qs.visible().filter(uuid=hidden_ledger.uuid).exists())

    def test_entity_slug_uses_manager_annotation_and_direct_instance_fallback(self):
        entity_model = self.create_entity(name="API Ledger Entity Slug Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-entity-slug",
        )

        annotated_ledger = LedgerModel.objects.get(uuid=ledger_model.uuid)
        direct_ledger = LedgerModel(
            name="API Direct Entity Slug Ledger",
            ledger_xid="api-direct-entity-slug",
            entity=entity_model,
        )

        self.assertEqual(annotated_ledger.entity_slug, entity_model.slug)
        self.assertEqual(direct_ledger.entity_slug, entity_model.slug)
