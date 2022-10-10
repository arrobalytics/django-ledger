"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from calendar import monthrange
from datetime import timedelta, date
from typing import Tuple

from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import Http404
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from django.views.generic.dates import YearMixin, MonthMixin, DayMixin

from django_ledger.models import EntityModel, InvoiceModel, BillModel
from django_ledger.models.entity import EntityReportMixIn
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

    def has_next_url(self):
        return self.request.GET.get('next') is not None

    def get_success_url(self):
        next = self.request.GET.get('next')
        if next:
            return next
        # elif self.kwargs.get('entity_slug'):
        #     return reverse('django_ledger:entity-dashboard',
        #                    kwargs={
        #                        'entity_slug': self.kwargs['entity_slug']
        #                    })
        return reverse('django_ledger:home')


class YearlyReportMixIn(YearMixin, EntityReportMixIn):

    def get_from_date(self, year: int = None, fy_start: int = None, **kwargs) -> date:
        return self.get_year_start_date(year, fy_start)

    def get_to_date(self, year: int = None, fy_start: int = None, **kwargs) -> date:
        return self.get_year_end_date(year, fy_start)

    def get_from_to_dates(self, year: int = None, fy_start: int = None, **kwargs) -> Tuple[date, date]:
        from_date = self.get_from_date(year, fy_start, **kwargs)
        to_date = self.get_to_date(year, fy_start, **kwargs)
        return from_date, to_date

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
        year_start = self.get_year_start_date(year)
        year_end = self.get_year_end_date(year)
        context['year_start'] = year_start
        context['year_end'] = year_end

        if 'from_date' not in context:
            context['from_date'] = year_start
        if 'to_date' not in context:
            context['to_date'] = year_end

        context['has_year'] = True
        return context


class QuarterlyReportMixIn(YearMixin, EntityReportMixIn):
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

    def get_from_to_dates(self,
                          quarter: int = None,
                          year: int = None,
                          fy_start: int = None,
                          **kwargs) -> Tuple[date, date]:
        from_date = self.get_from_date(quarter=quarter, year=year, fy_start=fy_start, **kwargs)
        to_date = self.get_to_date(quarter=quarter, year=year, fy_start=fy_start, **kwargs)
        return from_date, to_date

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
        context = super(QuarterlyReportMixIn, self).get_context_data(**kwargs)
        quarter = self.get_quarter()
        year = self.get_year()
        context['quarter'] = quarter
        context['next_quarter'] = self.get_next_quarter(quarter)
        context['previous_quarter'] = self.get_previous_quarter(quarter)
        quarter_start = self.get_quarter_start_date(year=year, quarter=quarter)
        quarter_end = self.get_quarter_end_date(year=year, quarter=quarter)
        context['quarter_start'] = quarter_start
        context['quarter_end'] = quarter_end

        if 'from_date' not in context:
            context['from_date'] = quarter_start
        if 'to_date' not in context:
            context['to_date'] = quarter_end

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

    def get_from_to_dates(self,
                          month: int = None,
                          year: int = None,
                          **kwargs) -> Tuple[date, date]:
        from_date = self.get_from_date(month=month, year=year, **kwargs)
        to_date = self.get_to_date(month=month, year=year, **kwargs)
        return from_date, to_date

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
        return date(year=year, month=month, day=last_day)

    def get_next_month(self, month) -> int:
        if month != 12:
            return month + 1
        return 1

    def get_previous_month(self, month) -> int:
        if month != 1:
            return month - 1
        return 12

    def get_context_data(self, **kwargs):
        context = super(MonthlyReportMixIn, self).get_context_data(**kwargs)
        month = int(self.get_month())
        year = int(self.get_year())
        context['month'] = month
        context['next_month'] = self.get_next_month(month)
        context['previous_month'] = self.get_previous_month(month)
        month_start = self.get_month_start_date(year=year, month=month)
        month_end = self.get_month_end_date(year=year, month=month)
        context['month_start'] = month_start
        context['month_end'] = month_end
        context['from_date'] = month_start
        context['to_date'] = month_end
        context['has_month'] = True
        return context


class DateReportMixIn(MonthlyReportMixIn, DayMixin):

    def get_context_data(self, **kwargs):
        context = super(MonthlyReportMixIn, self).get_context_data(**kwargs)
        view_date = self.get_date()
        context['has_date'] = True
        context['next_day'] = view_date + timedelta(days=1)
        context['previous_day'] = view_date - timedelta(days=1)
        context['view_date'] = view_date
        context['from_date'] = view_date
        context['to_date'] = view_date
        return context

    def get_date(self) -> date:
        return date(
            year=self.get_year(),
            month=self.get_month(),
            day=self.get_day()
        )

    def get_from_date(self, month: int = None, year: int = None, **kwargs) -> date:
        return self.get_date()

    def get_to_date(self, month: int = None, year: int = None, **kwargs) -> date:
        return self.get_date()

    def get_from_to_dates(self, month: int = None, year: int = None, **kwargs) -> Tuple[date, date]:
        dt = self.get_from_date(month=month, year=year, **kwargs)
        return dt, dt


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

    def get_from_to_dates(self, query_param: str = None) -> Tuple[date, date]:
        from_date = self.get_from_date(query_param)
        to_date = self.get_to_date(query_param)
        return from_date, to_date

    def parse_date_from_query_param(self, query_param: str):
        param_date = self.request.GET.get(query_param)
        if param_date:
            parsed_date = parse_date(param_date)
            if not parsed_date:
                raise Http404(_(f'Invalid {query_param} {param_date} provided'))
            param_date = parsed_date
        return param_date


class DjangoLedgerAccessMixIn(AccessMixin):

    def get_login_url(self):
        return reverse('django_ledger:login')


class DjangoLedgerPermissionMixIn(PermissionRequiredMixin):

    def has_permission(self):
        return self.request.user.is_authenticated


class DjangoLedgerSecurityMixIn(DjangoLedgerPermissionMixIn, DjangoLedgerAccessMixIn, LoginRequiredMixin):
    pass


class EntityUnitMixIn:
    UNIT_SLUG_KWARG = 'unit_slug'
    UNIT_SLUG_QUERY_PARAM = 'unit'

    def get_context_data(self, **kwargs):
        context = super(EntityUnitMixIn, self).get_context_data(**kwargs)
        context['unit_slug'] = self.get_unit_slug()
        return context

    def get_unit_slug(self):
        unit_slug = self.kwargs.get(self.UNIT_SLUG_KWARG)
        if not unit_slug:
            unit_slug = self.request.GET.get(self.UNIT_SLUG_QUERY_PARAM)
        return unit_slug


class EntityDigestMixIn:

    def get_entity_digest(self, context, from_date=None, end_date=None, **kwargs):
        by_period = self.request.GET.get('by_period')
        entity_model: EntityModel = self.object
        if not end_date:
            end_date = context['to_date']
        if not from_date:
            from_date = context['from_date']

        unit_slug = self.get_unit_slug()

        qs_all, digest = entity_model.digest(user_model=self.request.user,
                                             to_date=end_date,
                                             unit_slug=unit_slug,
                                             by_period=True if by_period else False,
                                             process_ratios=True,
                                             process_roles=True,
                                             process_groups=True)

        qs_equity, equity_digest = entity_model.digest(user_model=self.request.user,
                                                       digest_name='equity_digest',
                                                       to_date=end_date,
                                                       from_date=from_date,
                                                       unit_slug=unit_slug,
                                                       by_period=True if by_period else False,
                                                       process_ratios=False,
                                                       process_roles=False,
                                                       process_groups=True)
        context.update(digest)
        context.update(equity_digest)
        context['date_filter'] = end_date
        return context


class UnpaidElementsMixIn:
    FETCH_UNPAID_INVOICES: bool = False
    FETCH_UNPAID_BILLS: bool = False

    def get_context_data(self, **kwargs):
        context = super(UnpaidElementsMixIn, self).get_context_data(**kwargs)
        context['invoices'] = self.get_unpaid_invoices_qs(context)
        context['bills'] = self.get_unpaid_bills_qs(context)
        return context

    def get_unpaid_invoices_qs(self, context, from_date=None, to_date=None):
        if self.FETCH_UNPAID_INVOICES:
            from_date = context['from_date'] if not from_date else from_date
            to_date = context['to_date'] if not to_date else to_date

            qs = InvoiceModel.objects.for_entity(
                user_model=self.request.user,
                entity_slug=self.kwargs['entity_slug']
            ).approved().filter(
                Q(date_approved__gte=from_date) &
                Q(date_approved__lte=to_date)
            ).select_related('customer').order_by('date_due')

            unit_slug = self.get_unit_slug()
            if unit_slug:
                qs = qs.filter(ledger__journal_entries__entity_unit__slug__exact=unit_slug)

            return qs

    def get_unpaid_bills_qs(self, context, from_date=None, to_date=None):
        if self.FETCH_UNPAID_BILLS:
            from_date = context['from_date'] if not from_date else from_date
            to_date = context['to_date'] if not to_date else to_date

            qs = BillModel.objects.for_entity_unpaid(
                user_model=self.request.user,
                entity_slug=self.kwargs['entity_slug']
            ).filter(
                Q(date_approved__gte=from_date) &
                Q(date_approved__lte=to_date)
            ).select_related('vendor').order_by('date_due')

            unit_slug = self.get_unit_slug()
            if unit_slug:
                qs = qs.filter(ledger__journal_entries__entity_unit__slug__exact=unit_slug)

            return qs


class BaseDateNavigationUrlMixIn:
    BASE_DATE_URL_KWARGS = (
        'entity_slug',
        'unit_slug',
        'ledger_pk',
        'account_pk'
    )

    def get_context_data(self, **kwargs):
        context = super(BaseDateNavigationUrlMixIn, self).get_context_data(**kwargs)
        self.get_base_date_nav_url(context)
        return context

    def get_base_date_nav_url(self, context, **kwargs):
        view_name = context['view'].request.resolver_match.url_name
        view_name_base = '-'.join(view_name.split('-')[:2])
        context['date_navigation_url'] = reverse(f'django_ledger:{view_name_base}',
                                                 kwargs={
                                                     k: v for k, v in self.kwargs.items() if
                                                     k in self.BASE_DATE_URL_KWARGS
                                                 })
