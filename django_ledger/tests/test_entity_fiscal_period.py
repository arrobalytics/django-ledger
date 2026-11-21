"""
Characterization tests for EntityModelFiscalPeriodMixIn and EntityModel.default_coa_slug.

These tests pin down how Django Ledger works out the fiscal year start month, the fiscal year and quarter windows
built from it, and the default Chart of Accounts slug. They run without a database: every model instance is built
in memory and never saved.
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from django_ledger.models.accounts import AccountModel
from django_ledger.models.chart_of_accounts import ChartOfAccountModel
from django_ledger.models.entity import EntityModel, EntityModelFiscalPeriodMixIn
from django_ledger.models.ledger import LedgerModel
from django_ledger.models.unit import EntityUnitModel


class FiscalPeriodViewStandIn(EntityModelFiscalPeriodMixIn):
    """
    A minimal stand-in for a report view. It carries the two attributes a report view offers to the mixin:
    the object being displayed and the EntityModel authorized for the request.
    """

    def __init__(self, object_model=None, authorized_entity_model=None):
        self.object = object_model
        self.AUTHORIZED_ENTITY_MODEL = authorized_entity_model


class FiscalYearStartMonthTest(SimpleTestCase):
    """How get_fy_start_month() finds the month on an EntityModel and on a view."""

    APRIL = 4
    SEPTEMBER = 9

    def get_entity_model(self, fy_start_month: int = APRIL) -> EntityModel:
        return EntityModel(name='Fiscal Period Test Entity', fy_start_month=fy_start_month)

    def test_entity_model_uses_its_own_month(self):
        entity_model = self.get_entity_model(self.SEPTEMBER)
        self.assertEqual(entity_model.get_fy_start_month(), self.SEPTEMBER)

    def test_view_reads_month_from_the_entity_behind_its_object(self):
        entity_model = self.get_entity_model()
        coa_model = ChartOfAccountModel(entity=entity_model, name='Test CoA')
        objects = {
            'EntityModel': entity_model,
            'LedgerModel': LedgerModel(entity=entity_model, name='Test Ledger'),
            'EntityUnitModel': EntityUnitModel(entity=entity_model, name='Test Unit'),
            'AccountModel': AccountModel(coa_model=coa_model, name='Test Account'),
        }
        for model_name, object_model in objects.items():
            with self.subTest(object=model_name):
                view = FiscalPeriodViewStandIn(object_model=object_model)
                self.assertEqual(view.get_fy_start_month(), self.APRIL)

    def test_view_without_object_uses_the_authorized_entity(self):
        view = FiscalPeriodViewStandIn(authorized_entity_model=self.get_entity_model())
        self.assertEqual(view.get_fy_start_month(), self.APRIL)

    def test_view_object_takes_precedence_over_the_authorized_entity(self):
        view = FiscalPeriodViewStandIn(
            object_model=LedgerModel(entity=self.get_entity_model(self.SEPTEMBER), name='Test Ledger'),
            authorized_entity_model=self.get_entity_model(self.APRIL),
        )
        self.assertEqual(view.get_fy_start_month(), self.SEPTEMBER)


class FiscalYearWindowTest(SimpleTestCase):
    """Fiscal year and quarter dates built from the start month, including year wraps and leap years."""

    def get_entity_model(self, fy_start_month: int) -> EntityModel:
        return EntityModel(name='Fiscal Window Test Entity', fy_start_month=fy_start_month)

    def test_fiscal_year_dates_for_every_start_month(self):
        for fy_start_month in range(1, 13):
            with self.subTest(fy_start_month=fy_start_month):
                entity_model = self.get_entity_model(fy_start_month)
                fy_start, fy_end = entity_model.get_fiscal_year_dates(year=2025)
                self.assertEqual(fy_start, date(2025, fy_start_month, 1))
                next_fy_start = date(2026, fy_start_month, 1)
                self.assertEqual((next_fy_start - fy_end).days, 1)

    def test_fiscal_year_ending_in_february_respects_leap_years(self):
        entity_model = self.get_entity_model(3)
        self.assertEqual(entity_model.get_fy_end(year=2023), date(2024, 2, 29))
        self.assertEqual(entity_model.get_fy_end(year=2022), date(2023, 2, 28))

    def test_quarters_wrap_into_the_next_calendar_year(self):
        entity_model = self.get_entity_model(11)
        expected_quarters = {
            1: (date(2024, 11, 1), date(2025, 1, 31)),
            2: (date(2025, 2, 1), date(2025, 4, 30)),
            3: (date(2025, 5, 1), date(2025, 7, 31)),
            4: (date(2025, 8, 1), date(2025, 10, 31)),
        }
        for quarter, expected_dates in expected_quarters.items():
            with self.subTest(quarter=quarter):
                self.assertEqual(entity_model.get_fiscal_quarter_dates(year=2024, quarter=quarter), expected_dates)

    def test_fiscal_year_for_a_date(self):
        entity_model = self.get_entity_model(4)
        self.assertEqual(entity_model.get_fy_for_date(date(2024, 3, 31)), 2023)
        self.assertEqual(entity_model.get_fy_for_date(date(2024, 4, 1)), 2024)
        self.assertEqual(entity_model.get_fy_for_date(date(2024, 2, 29), as_str=True), '2023')

    def test_explicit_month_overrides_the_entity_setting(self):
        entity_model = self.get_entity_model(4)
        self.assertEqual(entity_model.get_fy_start(year=2024, fy_start_month=7), date(2024, 7, 1))

    def test_zero_month_argument_falls_back_to_the_entity_setting(self):
        entity_model = self.get_entity_model(4)
        self.assertEqual(entity_model.get_fy_start(year=2024, fy_start_month=0), date(2024, 4, 1))

    def test_invalid_explicit_month_is_rejected(self):
        entity_model = self.get_entity_model(4)
        with self.assertRaises(ValidationError):
            entity_model.get_fy_start(year=2024, fy_start_month=13)


class DefaultChartOfAccountsSlugTest(SimpleTestCase):
    """EntityModel.default_coa_slug prefers the manager annotation and falls back to the related chart."""

    def test_annotated_slug_is_used_when_present(self):
        entity_model = EntityModel(name='Annotated Entity')
        entity_model._default_coa_slug = 'annotated-coa'
        self.assertEqual(entity_model.default_coa_slug, 'annotated-coa')

    def test_annotated_none_is_returned_as_is(self):
        entity_model = EntityModel(name='Entity Without Default CoA')
        entity_model._default_coa_slug = None
        self.assertIsNone(entity_model.default_coa_slug)

    def test_related_chart_slug_is_used_without_annotation(self):
        coa_model = ChartOfAccountModel(name='Default CoA', slug='related-coa')
        entity_model = EntityModel(name='Plain Entity', default_coa=coa_model)
        self.assertEqual(entity_model.default_coa_slug, 'related-coa')
