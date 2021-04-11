"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from calendar import monthrange
from datetime import datetime, timedelta, date

from django.contrib.auth.mixins import LoginRequiredMixin as DJLoginRequiredMixIn
from django.core.exceptions import ValidationError
from django.http import Http404
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from django.views.generic.dates import YearMixin, MonthMixin, DayMixin

from django_ledger.models import EntityModel
from django_ledger.models.entity import EntityReportManager
from django_ledger.settings import DJANGO_LEDGER_LOGIN_URL
from django_ledger.utils import set_default_entity


class SessionConfigurationMixIn:

    def get(self, *args, **kwargs):
        response = super().get(*args, **kwargs)
        request = getattr(self, 'request')
        try:
            entity_model = getattr(self, 'object')
            if entity_model and isinstance(entity_model, EntityModel):
                set_default_entity(request, entity_model)
        except AttributeError:
            pass
        return response


class SuccessUrlNextMixIn:
    def get_success_url(self):
        next = self.request.GET.get('next')
        if next:
            return next
        elif self.kwargs.get('entity_slug'):
            return reverse('django_ledger:entity-dashboard',
                           kwargs={
                               'entity_slug': self.kwargs['entity_slug']
                           })
        return reverse('django_ledger:home')


class YearlyReportMixIn(YearMixin, EntityReportManager):

    def get_from_date(self, year: int = None, fy_start: int = None, **kwargs) -> date:
        return self.get_year_start_date(year, fy_start)

    def get_to_date(self, year: int = None, fy_start: int = None, **kwargs) -> date:
        return self.get_year_end_date(year, fy_start)

    def get_year_start_date(self, year: int = None, fy_start: int = None) -> date:
        if not year:
            year = self.get_year()
        return self.get_fy_start(year, fy_start)

    def get_year_end_date(self, year: int = None, fy_start: int = None) -> date:
        if not year:
            year = self.get_year()
        return self.get_fy_end(year, fy_start)

    def get_context_data(self, **kwargs):
        context = super(YearlyReportMixIn, self).get_context_data(**kwargs)
        year = self.get_year()
        context['year'] = year
        context['next_year'] = year + 1
        context['previous_year'] = year - 1
        context['from_date'] = self.get_year_start_date(year)
        context['to_date'] = self.get_year_end_date(year)
        context['has_year'] = True
        return context


class QuarterlyReportMixIn(YearMixin, EntityReportManager):
    quarter = None
    quarter_url_kwarg = 'quarter'

    def parse_quarter(self, quarter) -> int:
        try:
            if not isinstance(quarter, int):
                quarter = int(quarter)
            try:
                self.validate_quarter(quarter)
            except ValidationError:
                raise Http404(_("Invalid quarter number"))
        except ValueError:
            raise Http404(_(f"Invalid quarter format. Cannot parse {quarter} into integer."))
        return quarter

    def get_quarter(self) -> int:
        quarter = self.quarter
        if quarter is None:
            try:
                quarter = self.kwargs[self.quarter_url_kwarg]
            except KeyError:
                try:
                    quarter = self.request.GET[self.quarter_url_kwarg]
                except KeyError:
                    raise Http404(_("No quarter specified"))
        quarter = self.parse_quarter(quarter)
        return quarter

    def get_from_date(self, quarter: int = None, year: int = None, fy_start: int = None, **kwargs) -> date:
        return self.get_quarter_start_date(quarter, year, fy_start)

    def get_to_date(self, quarter: int = None, year: int = None, fy_start: int = None, **kwargs) -> date:
        return self.get_quarter_end_date(quarter, year, fy_start)

    def get_quarter_start_date(self, quarter: int = None, year: int = None, fy_start: int = None) -> date:
        if not year:
            year = self.get_year()
        if not quarter:
            quarter = self.get_quarter()
        return self.get_quarter_start(year, quarter, fy_start)

    def get_quarter_end_date(self, quarter: int = None, year: int = None, fy_start: int = None) -> date:
        if not year:
            year = self.get_year()
        if not quarter:
            quarter = self.get_quarter()
        return self.get_quarter_end(year, quarter, fy_start)

    def get_context_data(self, **kwargs) -> dict:
        quarter = self.get_quarter()
        year = self.get_year()
        context = super(QuarterlyReportMixIn, self).get_context_data(**kwargs)
        context['quarter'] = quarter
        context['next_quarter'] = self.get_next_quarter(quarter)
        context['previous_quarter'] = self.get_previous_quarter(quarter)
        context['from_date'] = self.get_quarter_start_date(year=year, quarter=quarter)
        context['to_date'] = self.get_quarter_end_date(year=year, quarter=quarter)
        context['has_quarter'] = True
        return context

    def get_next_quarter(self, quarter) -> int:
        if quarter != 4:
            return quarter + 1

    def get_previous_quarter(self, quarter) -> int:
        if quarter != 1:
            return quarter - 1


class MonthlyReportMixIn(YearlyReportMixIn, MonthMixin):

    def get_from_date(self, month: int = None, year: int = None, **kwargs) -> date:
        return self.get_month_start_date(month=month, year=year)

    def get_to_date(self, month: int = None, year: int = None, **kwargs) -> date:
        return self.get_month_end_date(month=month, year=year)

    def get_month_start_date(self, month: int = None, year: int = None) -> date:
        if not month:
            month = int(self.get_month())
        if not year:
            year = self.get_year()
        return date(year=year, month=month, day=1)

    def get_month_end_date(self, month: int = None, year: int = None) -> date:
        if not month:
            month = int(self.get_month())
        if not year:
            year = self.get_year()
        last_day = monthrange(year, month)[1]
        return datetime(year=year, month=month, day=last_day)

    def get_context_data(self, **kwargs):
        context = super(MonthlyReportMixIn, self).get_context_data(**kwargs)
        month = int(self.get_month())
        year = int(self.get_year())
        context['month'] = month
        context['next_month'] = self.get_next_month(month)
        context['previous_month'] = self.get_previous_month(month)
        context['from_date'] = self.get_month_start_date(month, year)
        context['to_date'] = self.get_month_end_date(month, year)
        context['has_month'] = True
        return context

    def get_next_month(self, month):
        if month != 12:
            return month + 1
        return 1

    def get_previous_month(self, month):
        if month != 1:
            return month - 1
        return 12


class DateReportMixIn(MonthlyReportMixIn, DayMixin):

    def get_context_data(self, **kwargs):
        context = super(DateReportMixIn, self).get_context_data(**kwargs)
        view_date = self.get_date()
        context['view_date'] = view_date
        context['next_day'] = view_date + timedelta(days=1)
        context['previous_day'] = view_date - timedelta(days=1)
        return context

    def get_date(self):
        return datetime(
            year=self.get_year(),
            month=self.get_month(),
            day=self.get_day()
        )


class FromToDatesMixIn:
    DJL_FROM_DATE_PARAM: str = 'from_date'
    DJL_TO_DATE_PARAM: str = 'to_date'
    DJL_NO_FROM_DATE_RAISE_404: bool = True
    DJL_NO_TO_DATE_RAISE_404: bool = True

    def get_from_date(self, query_param: str = None) -> date:
        if not query_param:
            query_param = self.DJL_FROM_DATE_PARAM
        parsed_date = self.parse_date_from_query_param(query_param)
        if not parsed_date and self.DJL_NO_FROM_DATE_RAISE_404:
            raise Http404(_(f'Must provide {query_param} date parameter.'))
        return parsed_date

    def get_to_date(self, query_param: str = None) -> date:
        if not query_param:
            query_param = self.DJL_TO_DATE_PARAM
        parsed_date = self.parse_date_from_query_param(query_param)
        if not parsed_date and self.DJL_NO_TO_DATE_RAISE_404:
            raise Http404(_(f'Must provide {query_param} date parameter.'))
        return parsed_date

    def parse_date_from_query_param(self, query_param: str):
        param_date = self.request.GET.get(query_param)
        if param_date:
            parsed_date = parse_date(param_date)
            if not parsed_date:
                raise Http404(_(f'Invalid {query_param} {param_date} provided'))
            param_date = parsed_date
        return param_date


class LoginRequiredMixIn(DJLoginRequiredMixIn):
    login_url = DJANGO_LEDGER_LOGIN_URL
    redirect_field_name = 'next'


class EntityUnitMixIn:
    UNIT_SLUG_KWARG = 'unit_slug'
    UNIT_SLUG_QUERY_PARAM = 'unit'

    def get_unit_slug(self):
        unit_slug = self.kwargs.get(self.UNIT_SLUG_KWARG)
        if not unit_slug:
            unit_slug = self.request.GET.get(self.UNIT_SLUG_QUERY_PARAM)
        return unit_slug
