"""
High-level API behavior tests for EntityModel fiscal period helpers.

These tests document deterministic fiscal-year and fiscal-quarter behavior
without requiring accounting fixtures.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from django_ledger.models.entity import EntityModel


class EntityFiscalPeriodAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="api_entity_fiscal_period_user",
            email="api-entity-fiscal-period-user@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Fiscal Period Entity", fy_start_month=1):
        return EntityModel.create_entity(
            name=name,
            admin=self.user,
            use_accrual_method=True,
            fy_start_month=fy_start_month,
        )

    def test_get_fy_start_month_returns_entity_setting(self):
        entity_model = self.create_entity(fy_start_month=4)

        self.assertEqual(entity_model.get_fy_start_month(), 4)

    def test_calendar_fiscal_year_start_end_and_date_lookup(self):
        entity_model = self.create_entity(fy_start_month=1)

        self.assertEqual(entity_model.get_fy_start(2026), date(2026, 1, 1))
        self.assertEqual(entity_model.get_fy_end(2026), date(2026, 12, 31))

        self.assertEqual(entity_model.get_fy_for_date(date(2026, 1, 1)), 2026)
        self.assertEqual(entity_model.get_fy_for_date(date(2026, 12, 31)), 2026)
        self.assertEqual(entity_model.get_fy_for_date(date(2026, 6, 15), as_str=True), "2026")

    def test_april_fiscal_year_start_end_and_date_lookup(self):
        entity_model = self.create_entity(fy_start_month=4)

        self.assertEqual(entity_model.get_fy_start(2026), date(2026, 4, 1))
        self.assertEqual(entity_model.get_fy_end(2026), date(2027, 3, 31))

        self.assertEqual(entity_model.get_fy_for_date(date(2026, 3, 31)), 2025)
        self.assertEqual(entity_model.get_fy_for_date(date(2026, 4, 1)), 2026)
        self.assertEqual(entity_model.get_fy_for_date(date(2027, 3, 31)), 2026)
        self.assertEqual(entity_model.get_fy_for_date(date(2026, 4, 1), as_str=True), "2026")

    def test_explicit_fiscal_year_start_month_override_uses_requested_calendar(self):
        entity_model = self.create_entity(fy_start_month=4)

        self.assertEqual(entity_model.get_fy_start(2026, fy_start_month=1), date(2026, 1, 1))
        self.assertEqual(entity_model.get_fy_end(2026, fy_start_month=1), date(2026, 12, 31))
        self.assertEqual(
            entity_model.get_fiscal_year_dates(2026, fy_start_month=1),
            (date(2026, 1, 1), date(2026, 12, 31)),
        )

    def test_fiscal_year_end_uses_last_day_of_leap_year_february(self):
        entity_model = self.create_entity(fy_start_month=3)

        self.assertEqual(entity_model.get_fy_start(2023), date(2023, 3, 1))
        self.assertEqual(entity_model.get_fy_end(2023), date(2024, 2, 29))

    def test_april_fiscal_quarters_roll_across_calendar_year(self):
        entity_model = self.create_entity(fy_start_month=4)

        self.assertEqual(entity_model.get_quarter_start(2026, 1), date(2026, 4, 1))
        self.assertEqual(entity_model.get_quarter_end(2026, 1), date(2026, 6, 30))

        self.assertEqual(entity_model.get_quarter_start(2026, 2), date(2026, 7, 1))
        self.assertEqual(entity_model.get_quarter_end(2026, 2), date(2026, 9, 30))

        self.assertEqual(entity_model.get_quarter_start(2026, 3), date(2026, 10, 1))
        self.assertEqual(entity_model.get_quarter_end(2026, 3), date(2026, 12, 31))

        self.assertEqual(entity_model.get_quarter_start(2026, 4), date(2027, 1, 1))
        self.assertEqual(entity_model.get_quarter_end(2026, 4), date(2027, 3, 31))

    def test_fiscal_year_and_quarter_date_helpers_return_ranges(self):
        entity_model = self.create_entity(fy_start_month=4)

        self.assertEqual(
            entity_model.get_fiscal_year_dates(2026),
            (date(2026, 4, 1), date(2027, 3, 31)),
        )
        self.assertEqual(
            entity_model.get_fiscal_quarter_dates(2026, 4),
            (date(2027, 1, 1), date(2027, 3, 31)),
        )

    def test_invalid_month_and_quarter_raise_validation_error(self):
        entity_model = self.create_entity(fy_start_month=4)

        with self.assertRaises(ValidationError):
            entity_model.validate_month(0)

        with self.assertRaises(ValidationError):
            entity_model.validate_month(13)

        with self.assertRaises(ValidationError):
            entity_model.validate_quarter(0)

        with self.assertRaises(ValidationError):
            entity_model.validate_quarter(5)

        with self.assertRaises(ValidationError):
            entity_model.get_fy_start(2026, fy_start_month=13)

        with self.assertRaises(ValidationError):
            entity_model.get_fiscal_quarter_dates(2026, 5)
