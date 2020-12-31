"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from calendar import monthrange
from datetime import datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin as DJLoginRequiredMixIn
from django.http import Http404
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from django.views.generic.dates import YearMixin, MonthMixin, DayMixin

from django_ledger.settings import DJANGO_LEDGER_LOGIN_URL


class SuccessUrlNextMixIn:
    def get_success_url(self):
        next = self.request.GET.get('next')
        if next:
            return next
        elif self.kwargs.get('entity_slug'):
            return reverse('django_ledger:entity-dashboard', kwargs={
                'entity_slug': self.kwargs['entity_slug']
            })
        return reverse('django_ledger:home')


class YearlyReportMixIn(YearMixin):

    def get_from_date(self, year: int = None, **kwargs):
        return self.get_year_start_date(year)

    def get_to_date(self, year: int = None, **kwargs):
        return self.get_year_end_date(year)

    def get_year_start_date(self, year: int = None) -> datetime:
        if not year:
            year = self.get_year()
        return datetime(year=year, month=1, day=1)

    def get_year_end_date(self, year: int = None) -> datetime:
        if not year:
            year = self.get_year()
        return datetime(year=year, month=12, day=31)

    def get_context_data(self, **kwargs):
        context = super(YearlyReportMixIn, self).get_context_data(**kwargs)
        year = self.get_year()
        context['year'] = year
        context['next_year'] = year + 1
        context['previous_year'] = year - 1
        context['start_date'] = self.get_year_start_date(year)
        context['end_date'] = self.get_year_end_date(year)
        context['has_year'] = True
        return context


class QuarterlyReportMixIn(YearMixin):
    quarter = None
    quarter_url_kwarg = 'quarter'
    valid_quarters = [1, 2, 3, 4]

    def get_from_date(self, quarter: int = None, year: int = None, **kwargs) -> datetime:
        return self.get_quarter_start_date(quarter, year)

    def get_to_date(self, quarter: int = None, year: int = None, **kwargs) -> datetime:
        return self.get_quarter_end_date(quarter, year)

    def get_quarter_start_date(self, quarter: int = None, year: int = None) -> datetime:
        if not year:
            year = self.get_year()
        if not quarter:
            quarter = self.get_quarter()
        month = quarter * 3 - 2
        return datetime(year=year, month=month, day=1)

    def get_quarter_end_date(self, quarter: int = None, year: int = None) -> datetime:
        if not year:
            year = self.get_year()
        if not quarter:
            quarter = self.get_quarter()
        month = quarter * 3
        last_day = monthrange(year, month)[1]
        return datetime(year=year, month=month, day=last_day)

    def get_context_data(self, **kwargs) -> dict:
        quarter = self.get_quarter()
        year = self.get_year()
        context = super(QuarterlyReportMixIn, self).get_context_data(**kwargs)
        context['quarter'] = quarter
        context['next_quarter'] = self.get_next_quarter(quarter)
        context['previous_quarter'] = self.get_previous_quarter(quarter)
        context['start_date'] = self.get_quarter_start_date(year=year, quarter=quarter)
        context['end_date'] = self.get_quarter_end_date(year=year, quarter=quarter)
        context['has_quarter'] = True
        return context

    def validate_quarter(self, quarter) -> int:
        try:
            if not isinstance(quarter, int):
                quarter = int(quarter)
            if quarter not in self.valid_quarters:
                raise Http404(_("Invalid quarter number"))
        except ValueError:
            raise Http404(_("Invalid quarter format"))
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
        quarter = self.validate_quarter(quarter)
        return quarter

    def get_next_quarter(self, quarter) -> int:
        if quarter != 4:
            return quarter + 1

    def get_previous_quarter(self, quarter) -> int:
        if quarter != 1:
            return quarter - 1


class MonthlyReportMixIn(YearlyReportMixIn, MonthMixin):

    def get_from_date(self, month: int = None, year: int = None, **kwargs):
        return self.get_month_start_date(month=month, year=year)

    def get_to_date(self, month: int = None, year: int = None, **kwargs):
        return self.get_month_end_date(month=month, year=year)

    def get_month_start_date(self, month: int = None, year: int = None):
        if not month:
            month = int(self.get_month())
        if not year:
            year = self.get_year()
        return datetime(year=year, month=month, day=1)

    def get_month_end_date(self, month: int = None, year: int = None):
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
        context['start_date'] = self.get_month_start_date(month, year)
        context['end_date'] = self.get_month_end_date(month, year)
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

    def get_from_date(self, query_param: str = None):
        if not query_param:
            query_param = self.DJL_FROM_DATE_PARAM
        parsed_date = self.parse_date_from_query_param(query_param)
        if not parsed_date and self.DJL_NO_FROM_DATE_RAISE_404:
            raise Http404(_(f'Must provide {query_param} date parameter.'))
        return parsed_date

    def get_to_date(self, query_param: str = None):
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
