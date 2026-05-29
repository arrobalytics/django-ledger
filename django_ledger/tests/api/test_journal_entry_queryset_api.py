"""
High-level API behavior tests for JournalEntryModel manager and queryset helpers.

These tests cover entity/user scoping, public queryset filters, ledger scoping,
and annotated property fallbacks without requiring transaction fixtures.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel
from django_ledger.models.entity import EntityManagementModel, EntityModel
from django_ledger.models.journal_entry import JournalEntryValidationError


class JournalEntryQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_je_queryset_admin",
            email="api-je-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_je_queryset_other_admin",
            email="api-je-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_je_queryset_manager",
            email="api-je-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_je_queryset_unrelated",
            email="api-je-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_je_queryset_superuser",
            email="api-je-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity(
        self,
        *,
        name="API Journal Entry QuerySet Entity",
        admin=None,
        last_closing_date=None,
    ):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=admin or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        if last_closing_date is not None:
            entity_model.last_closing_date = last_closing_date
            entity_model.save(update_fields=["last_closing_date", "updated"])
        return entity_model

    def create_ledger(
        self,
        entity_model,
        *,
        name="API Journal Entry QuerySet Ledger",
        ledger_xid="api-je-queryset-ledger",
        locked=False,
    ):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=ledger_xid,
            entity=entity_model,
            locked=locked,
        )

    def create_journal_entry(
        self,
        ledger_model,
        *,
        description="API Journal Entry QuerySet Journal Entry",
        posted=False,
        locked=False,
        force_create=False,
    ):
        create_kwargs = {
            "ledger": ledger_model,
            "timestamp": self.make_timestamp(),
            "description": description,
            "posted": posted,
            "locked": locked,
        }
        if force_create:
            create_kwargs["force_create"] = True
        return JournalEntryModel.objects.create(**create_kwargs)

    def test_for_entity_accepts_model_slug_and_uuid(self):
        entity_model = self.create_entity(name="API JE For Entity A")
        other_entity = self.create_entity(
            name="API JE For Entity B",
            admin=self.other_admin_user,
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-je-for-entity-a",
        )
        other_ledger = self.create_ledger(
            other_entity,
            ledger_xid="api-je-for-entity-b",
        )
        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE For Entity A",
        )
        other_journal_entry = self.create_journal_entry(
            other_ledger,
            description="API JE For Entity B",
        )

        for entity_lookup in (entity_model, entity_model.slug, entity_model.uuid):
            with self.subTest(entity_lookup=entity_lookup):
                journal_entry_qs = JournalEntryModel.objects.for_entity(entity_lookup)

                self.assertTrue(journal_entry_qs.filter(uuid=journal_entry.uuid).exists())
                self.assertFalse(journal_entry_qs.filter(uuid=other_journal_entry.uuid).exists())

    def test_for_entity_rejects_invalid_input(self):
        with self.assertRaises(JournalEntryValidationError):
            JournalEntryModel.objects.for_entity(object())

    def test_for_user_scopes_journal_entries_by_entity_access(self):
        entity_model = self.create_entity(name="API JE User Scope Entity")
        other_entity = self.create_entity(
            name="API JE Other User Scope Entity",
            admin=self.other_admin_user,
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-je-user-scope",
        )
        other_ledger = self.create_ledger(
            other_entity,
            ledger_xid="api-je-other-user-scope",
        )
        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE User Scope",
        )
        other_journal_entry = self.create_journal_entry(
            other_ledger,
            description="API JE Other User Scope",
        )

        EntityManagementModel.objects.create(
            entity=entity_model,
            user=self.manager_user,
            permission_level="read",
        )

        admin_qs = JournalEntryModel.objects.for_user(self.admin_user)
        manager_qs = JournalEntryModel.objects.for_user(self.manager_user)
        unrelated_qs = JournalEntryModel.objects.for_user(self.unrelated_user)
        superuser_qs = JournalEntryModel.objects.for_user(self.superuser)

        self.assertTrue(admin_qs.filter(uuid=journal_entry.uuid).exists())
        self.assertFalse(admin_qs.filter(uuid=other_journal_entry.uuid).exists())

        self.assertTrue(manager_qs.filter(uuid=journal_entry.uuid).exists())
        self.assertFalse(manager_qs.filter(uuid=other_journal_entry.uuid).exists())

        self.assertFalse(unrelated_qs.filter(uuid=journal_entry.uuid).exists())
        self.assertFalse(unrelated_qs.filter(uuid=other_journal_entry.uuid).exists())

        self.assertTrue(superuser_qs.filter(uuid=journal_entry.uuid).exists())
        self.assertTrue(superuser_qs.filter(uuid=other_journal_entry.uuid).exists())

    def test_queryset_filters_return_matching_journal_entries(self):
        entity_model = self.create_entity(name="API JE Filter Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-je-filter-ledger",
        )
        posted_journal_entry = self.create_journal_entry(
            ledger_model,
            description="API Posted JE",
            posted=True,
            locked=False,
            force_create=True,
        )
        unposted_journal_entry = self.create_journal_entry(
            ledger_model,
            description="API Unposted JE",
            posted=False,
        )
        locked_journal_entry = self.create_journal_entry(
            ledger_model,
            description="API Locked JE",
            locked=True,
        )
        unlocked_journal_entry = self.create_journal_entry(
            ledger_model,
            description="API Unlocked JE",
            locked=False,
        )

        journal_entry_qs = JournalEntryModel.objects.for_entity(entity_model)

        self.assertTrue(journal_entry_qs.posted().filter(uuid=posted_journal_entry.uuid).exists())
        self.assertFalse(journal_entry_qs.posted().filter(uuid=unposted_journal_entry.uuid).exists())

        self.assertTrue(journal_entry_qs.unposted().filter(uuid=unposted_journal_entry.uuid).exists())
        self.assertFalse(journal_entry_qs.unposted().filter(uuid=posted_journal_entry.uuid).exists())

        self.assertTrue(journal_entry_qs.locked().filter(uuid=locked_journal_entry.uuid).exists())
        self.assertFalse(journal_entry_qs.locked().filter(uuid=unlocked_journal_entry.uuid).exists())

        self.assertTrue(journal_entry_qs.unlocked().filter(uuid=unlocked_journal_entry.uuid).exists())
        self.assertFalse(journal_entry_qs.unlocked().filter(uuid=locked_journal_entry.uuid).exists())

    def test_for_ledger_accepts_model_uuid_and_uuid_string(self):
        entity_model = self.create_entity(name="API JE For Ledger Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-je-for-ledger-a",
        )
        other_ledger = self.create_ledger(
            entity_model,
            ledger_xid="api-je-for-ledger-b",
        )
        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE For Ledger A",
        )
        other_journal_entry = self.create_journal_entry(
            other_ledger,
            description="API JE For Ledger B",
        )

        for ledger_lookup in (ledger_model, ledger_model.uuid, str(ledger_model.uuid)):
            with self.subTest(ledger_lookup=ledger_lookup):
                journal_entry_qs = JournalEntryModel.objects.for_ledger(ledger_lookup)

                self.assertTrue(journal_entry_qs.filter(uuid=journal_entry.uuid).exists())
                self.assertFalse(journal_entry_qs.filter(uuid=other_journal_entry.uuid).exists())

    def test_manager_annotations_and_property_fallbacks_expose_entity_and_ledger_state(self):
        entity_model = self.create_entity(
            name="API JE Annotation Entity",
            last_closing_date=date(2026, 1, 31),
        )
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-je-annotation-ledger",
            locked=False,
        )
        journal_entry = self.create_journal_entry(
            ledger_model,
            description="API JE Annotation",
        )
        ledger_model.locked = True
        ledger_model.save(update_fields=["locked", "updated"])

        annotated_journal_entry = JournalEntryModel.objects.get(uuid=journal_entry.uuid)
        direct_journal_entry = JournalEntryModel(
            ledger=ledger_model,
            timestamp=self.make_timestamp(),
            description="API Direct JE Annotation",
        )

        self.assertEqual(annotated_journal_entry.entity_uuid, entity_model.uuid)
        self.assertEqual(direct_journal_entry.entity_uuid, entity_model.uuid)

        self.assertEqual(annotated_journal_entry.entity_slug, entity_model.slug)
        self.assertEqual(direct_journal_entry.entity_slug, entity_model.slug)

        self.assertEqual(annotated_journal_entry.entity_last_closing_date, date(2026, 1, 31))
        self.assertEqual(direct_journal_entry.entity_last_closing_date, date(2026, 1, 31))

        self.assertTrue(annotated_journal_entry.ledger_is_locked())
        self.assertTrue(direct_journal_entry.ledger_is_locked())

        self.assertTrue(hasattr(annotated_journal_entry, "txs_count"))
        self.assertEqual(annotated_journal_entry.txs_count, 0)
