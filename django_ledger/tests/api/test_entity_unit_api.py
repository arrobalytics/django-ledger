"""
High-level API behavior tests for EntityUnitModel.

This file is part of a human-reviewed, AI-assisted contribution using
OpenAI GPT-5.5. The goal is to strengthen deterministic business-logic
coverage around Django Ledger's public/high-level API contracts without
replacing or reorganizing the existing test suite.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from django_ledger.models import JournalEntryModel, LedgerModel
from django_ledger.models.entity import EntityModel, EntityStateModel
from django_ledger.models.unit import EntityUnitModel, EntityUnitModelValidationError


class EntityUnitHighLevelAPITest(TestCase):
    """
    High-level behavior tests for EntityUnitModel contracts.

    These tests intentionally avoid the randomized/populated test base. The
    purpose is to document deterministic entity-unit invariants that should
    remain true across swappable-model refactors.
    """

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="api_entity_unit_contract_user",
            email="api-entity-unit-contract-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def make_timestamp(self):
        if settings.USE_TZ:
            return datetime(2026, 1, 15, 12, 0, tzinfo=ZoneInfo(settings.TIME_ZONE))
        return datetime(2026, 1, 15, 12, 0)

    def create_entity_setup(self, *, name="API Entity Unit Contract Entity"):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=1,
        )

        return {
            "entity_model": entity_model,
        }

    def create_unit(
        self,
        setup,
        *,
        name="API Entity Unit",
        slug="api-entity-unit",
        document_prefix="AEU",
        active=True,
        hidden=False,
    ):
        unit_model = EntityUnitModel.add_root(
            name=name,
            slug=slug,
            entity=setup["entity_model"],
            document_prefix=document_prefix,
            active=active,
            hidden=hidden,
        )

        unit_model.refresh_from_db()
        return unit_model

    def create_ledger(self, setup):
        ledger_model, _created = LedgerModel.objects.get_or_create(
            entity=setup["entity_model"],
            ledger_xid="api-entity-unit-ledger",
            defaults={
                "name": "API Entity Unit Ledger",
            },
        )

        return ledger_model

    def create_journal_entry(self, setup, *, unit_model=None):
        ledger_model = self.create_ledger(setup)

        journal_entry = JournalEntryModel.objects.create(
            ledger=ledger_model,
            entity_unit=unit_model,
            timestamp=self.make_timestamp(),
            description="API Entity Unit Journal Entry",
        )

        journal_entry.generate_je_number(commit=True)
        journal_entry.refresh_from_db()

        return journal_entry

    def get_je_state(self, setup, *, unit_model=None):
        fy_key = setup["entity_model"].get_fy_for_date(dt=self.make_timestamp())

        return EntityStateModel.objects.get(
            entity_model=setup["entity_model"],
            entity_unit=unit_model,
            fiscal_year=fy_key,
            key=EntityStateModel.KEY_JOURNAL_ENTRY,
        )

    def test_entity_unit_creation_binds_entity_and_preserves_public_fields(self):
        setup = self.create_entity_setup()

        unit_model = self.create_unit(setup)

        self.assertIsInstance(unit_model, EntityUnitModel)
        self.assertIsNotNone(unit_model.uuid)
        self.assertEqual(unit_model.entity_id, setup["entity_model"].uuid)
        self.assertEqual(unit_model.name, "API Entity Unit")
        self.assertEqual(unit_model.slug, "api-entity-unit")
        self.assertEqual(unit_model.document_prefix, "AEU")
        self.assertTrue(unit_model.active)
        self.assertFalse(unit_model.hidden)

    def test_entity_unit_for_entity_limits_queryset_to_entity_scope(self):
        setup = self.create_entity_setup(name="API Entity Unit Entity A")
        other_setup = self.create_entity_setup(name="API Entity Unit Entity B")

        unit_model = self.create_unit(
            setup,
            name="API Unit A",
            slug="api-unit-a",
            document_prefix="AUA",
        )

        other_unit_model = self.create_unit(
            other_setup,
            name="API Unit B",
            slug="api-unit-b",
            document_prefix="AUB",
        )

        scoped_qs = EntityUnitModel.objects.for_entity(setup["entity_model"])

        self.assertTrue(scoped_qs.filter(uuid=unit_model.uuid).exists())
        self.assertFalse(scoped_qs.filter(uuid=other_unit_model.uuid).exists())

    def test_entity_unit_for_entity_accepts_slug_and_uuid(self):
        setup = self.create_entity_setup()

        unit_model = self.create_unit(setup)

        by_slug_qs = EntityUnitModel.objects.for_entity(setup["entity_model"].slug)
        by_uuid_qs = EntityUnitModel.objects.for_entity(setup["entity_model"].uuid)

        self.assertTrue(by_slug_qs.filter(uuid=unit_model.uuid).exists())
        self.assertTrue(by_uuid_qs.filter(uuid=unit_model.uuid).exists())

    def test_entity_unit_for_entity_rejects_invalid_input(self):
        with self.assertRaises(EntityUnitModelValidationError):
            EntityUnitModel.objects.for_entity(None)

    def test_entity_unit_validate_for_entity_accepts_matching_entity_variants(self):
        setup = self.create_entity_setup()

        unit_model = self.create_unit(setup)

        unit_model.validate_for_entity(setup["entity_model"])
        unit_model.validate_for_entity(setup["entity_model"].uuid)
        unit_model.validate_for_entity(setup["entity_model"].slug)

    def test_entity_unit_validate_for_entity_rejects_mismatched_entity(self):
        setup = self.create_entity_setup(name="API Entity Unit Entity A")
        other_setup = self.create_entity_setup(name="API Entity Unit Entity B")

        unit_model = self.create_unit(setup)

        with self.assertRaises(EntityUnitModelValidationError):
            unit_model.validate_for_entity(other_setup["entity_model"])

    def test_entity_unit_document_prefix_is_unique_within_entity(self):
        setup = self.create_entity_setup()

        self.create_unit(
            setup,
            name="API Unit A",
            slug="api-unit-a",
            document_prefix="DUP",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_unit(
                    setup,
                    name="API Unit B",
                    slug="api-unit-b",
                    document_prefix="DUP",
                )

    def test_entity_unit_slug_is_unique_within_entity(self):
        setup = self.create_entity_setup()

        self.create_unit(
            setup,
            name="API Unit A",
            slug="api-unit",
            document_prefix="AUA",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_unit(
                    setup,
                    name="API Unit B",
                    slug="api-unit",
                    document_prefix="AUB",
                )

    def test_entity_unit_clean_generates_slug_and_document_prefix_when_missing(self):
        setup = self.create_entity_setup()

        unit_model = EntityUnitModel.add_root(
            name="API Generated Unit",
            entity=setup["entity_model"],
        )

        unit_model.clean()
        unit_model.save()
        unit_model.refresh_from_db()

        self.assertTrue(unit_model.slug)
        self.assertTrue(unit_model.slug.startswith("api-generated-unit"))
        self.assertTrue(unit_model.document_prefix)
        self.assertEqual(len(unit_model.document_prefix), 3)

    def test_journal_entry_numbering_state_is_scoped_by_entity_unit(self):
        setup = self.create_entity_setup()

        unit_a = self.create_unit(
            setup,
            name="API Unit A",
            slug="api-unit-a",
            document_prefix="AUA",
        )

        unit_b = self.create_unit(
            setup,
            name="API Unit B",
            slug="api-unit-b",
            document_prefix="AUB",
        )

        self.create_journal_entry(setup, unit_model=unit_a)
        self.create_journal_entry(setup, unit_model=unit_a)
        self.create_journal_entry(setup, unit_model=unit_b)

        state_a = self.get_je_state(setup, unit_model=unit_a)
        state_b = self.get_je_state(setup, unit_model=unit_b)

        self.assertEqual(state_a.sequence, 2)
        self.assertEqual(state_b.sequence, 1)
        self.assertEqual(state_a.entity_unit_id, unit_a.uuid)
        self.assertEqual(state_b.entity_unit_id, unit_b.uuid)

    def test_journal_entry_numbering_state_separates_unit_and_no_unit_sequences(self):
        setup = self.create_entity_setup()

        unit_model = self.create_unit(setup)

        self.create_journal_entry(setup, unit_model=unit_model)
        self.create_journal_entry(setup, unit_model=None)

        unit_state = self.get_je_state(setup, unit_model=unit_model)
        no_unit_state = self.get_je_state(setup, unit_model=None)

        self.assertEqual(unit_state.sequence, 1)
        self.assertEqual(no_unit_state.sequence, 1)
        self.assertEqual(unit_state.entity_unit_id, unit_model.uuid)
        self.assertIsNone(no_unit_state.entity_unit_id)
