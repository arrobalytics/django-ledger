from calendar import monthrange
from datetime import datetime

from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic.dates import YearMixin, MonthMixin


class YearlyReportMixIn(YearMixin):

    def get_context_data(self, **kwargs):
        context = super(YearlyReportMixIn, self).get_context_data(**kwargs)
        year = self.get_year()
        context['year'] = year
        context['next_year'] = year + 1
        context['previous_year'] = year - 1
        context['start_date'] = datetime(year=year, month=1, day=1)
        context['end_date'] = datetime(year=year, month=12, day=31)
        return context


class QuarterlyReportMixIn(YearMixin):
    quarter = None
    quarter_url_kwarg = 'quarter'
    valid_quarters = [1, 2, 3, 4]

    def get_context_data(self, **kwargs):
        quarter = self.get_quarter()
        year = self.get_year()
        context = super(QuarterlyReportMixIn, self).get_context_data(**kwargs)
        context['quarter'] = quarter
        context['next_quarter'] = self.get_next_quarter(quarter)
        context['previous_quarter'] = self.get_previous_quarter(quarter)
        context['start_date'] = self.get_quarter_start_date(year=year, quarter=quarter)
        context['end_date'] = self.get_quarter_end_date(year=year, quarter=quarter)
        return context

    def validate_quarter(self, quarter):
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

    def get_quarter_start_date(self, quarter: int, year: int = None) -> datetime:
        if not year:
            year = self.get_year()
        month = quarter * 3 - 2
        return datetime(year=year, month=month, day=1)

    def get_quarter_end_date(self, quarter: int, year: int = None) -> datetime:
        if not year:
            year = self.get_year()
        month = quarter * 3
        last_day = monthrange(year, month)[1]
        return datetime(year=year, month=month, day=last_day)


class MonthlyReportMixIn(YearlyReportMixIn, MonthMixin):

    def get_context_data(self, **kwargs):
        context = super(MonthlyReportMixIn, self).get_context_data(**kwargs)
        month = int(self.get_month())
        year = int(self.get_year())
        context['month'] = month
        context['next_month'] = self.get_next_month(month)
        context['previous_month'] = self.get_previous_month(month)
        context['start_date'] = self.get_month_start_date(month, year)
        context['end_date'] = self.get_month_end_date(month, year)
        return context

    def get_next_month(self, month):
        if month != 12:
            return month + 1
        return 1

    def get_previous_month(self, month):
        if month != 1:
            return month - 1
        return 12

    def get_month_start_date(self, month, year):
        return datetime(year=year, month=month, day=1)

    def get_month_end_date(self, month, year):
        last_day = monthrange(year, month)[1]
        return datetime(year=year, month=month, day=last_day)
