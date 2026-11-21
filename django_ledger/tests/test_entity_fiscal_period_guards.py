"""
Tests for the fiscal year start month guards: a missing month falls back to DEFAULT_FY_START_MONTH, an invalid
month is rejected, and a view without any EntityModel behind it gets a clear error.
"""

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from django_ledger.models.entity import (
    DEFAULT_FY_START_MONTH,
    EntityModel,
    EntityModelFiscalPeriodMixIn,
    EntityModelValidationError,
)
from django_ledger.models.receipt import ReceiptModel


class FiscalPeriodViewStandIn(EntityModelFiscalPeriodMixIn):
    """A minimal stand-in for a report view, carrying an object and the EntityModel authorized for the request."""

    def __init__(self, object_model=None, authorized_entity_model=None):
        self.object = object_model
        self.AUTHORIZED_ENTITY_MODEL = authorized_entity_model


class FiscalYearStartMonthGuardTest(SimpleTestCase):

    def test_missing_month_falls_back_to_the_default(self):
        entity_model = EntityModel(name='Entity Without Month', fy_start_month=None)
        self.assertEqual(entity_model.get_fy_start_month(), DEFAULT_FY_START_MONTH)

    def test_out_of_range_month_is_rejected(self):
        for fy_start_month in (0, 13):
            with self.subTest(fy_start_month=fy_start_month):
                entity_model = EntityModel(name='Entity With Bad Month', fy_start_month=fy_start_month)
                with self.assertRaises(ValidationError):
                    entity_model.get_fy_start_month()

    def test_unrelated_object_falls_back_to_the_authorized_entity(self):
        view = FiscalPeriodViewStandIn(
            object_model=ReceiptModel(),
            authorized_entity_model=EntityModel(name='Authorized Entity', fy_start_month=7),
        )
        self.assertEqual(view.get_fy_start_month(), 7)

    def test_view_without_any_entity_raises_a_clear_error(self):
        with self.assertRaises(EntityModelValidationError):
            FiscalPeriodViewStandIn().get_fy_start_month()

    def test_default_month_matches_the_field_default(self):
        self.assertEqual(EntityModel._meta.get_field('fy_start_month').default, DEFAULT_FY_START_MONTH)
