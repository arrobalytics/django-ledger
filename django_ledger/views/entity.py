"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import timedelta
from random import randint

from django.db.models import Q
from django.urls import reverse
from django.utils.timezone import localtime, localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView, DeleteView

from django_ledger.forms.app_filters import AsOfDateFilterForm, EntityFilterForm
from django_ledger.forms.entity import EntityModelUpdateForm, EntityModelCreateForm
from django_ledger.models.bill import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.utils import (
    get_default_entity_session_key,
    populate_default_coa, generate_sample_data, set_default_entity,
    set_end_date_filter
)
from django_ledger.views.mixins import (
    QuarterlyReportMixIn, YearlyReportMixIn,
    MonthlyReportMixIn, DateReportMixIn, FromToDatesMixIn
)


# Entity CRUD Views ----
class EntityModelListView(ListView):
    template_name = 'django_ledger/entitiy_list.html'
    context_object_name = 'entities'
    PAGE_TITLE = _('My Entities')
    extra_context = {
        'header_title': PAGE_TITLE,
        'page_title': PAGE_TITLE
    }

    def get_queryset(self):
        return EntityModel.objects.for_user(
            user_model=self.request.user)


class EntityModelCreateView(CreateView):
    template_name = 'django_ledger/entity_create.html'
    form_class = EntityModelCreateForm
    PAGE_TITLE = _('Create Entity')
    extra_context = {
        'header_title': PAGE_TITLE,
        'page_title': PAGE_TITLE
    }

    def get_success_url(self):
        return reverse('django_ledger:home')

    def form_valid(self, form):
        user = self.request.user
        form.instance.admin = user
        entity = form.save()
        default_coa = form.cleaned_data.get('default_coa')
        activate_accounts = form.cleaned_data.get('activate_all_accounts')
        if default_coa:
            populate_default_coa(entity_model=entity, activate_accounts=activate_accounts)

        sample_data = form.cleaned_data.get('generate_sample_data')
        if sample_data:
            generate_sample_data(
                entity=entity.slug,
                user_model=self.request.user,
                start_dt=localtime() - timedelta(days=30 * 6),
                days_fw=30 * 9,
                tx_quantity=50
            )
        self.object = entity
        return super().form_valid(form)


class EntityModelUpdateView(UpdateView):
    context_object_name = 'entity'
    template_name = 'django_ledger/entity_update.html'
    form_class = EntityModelUpdateForm
    slug_url_kwarg = 'entity_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        context['header_title'] = self.object.name
        return context

    def get_success_url(self):
        return reverse('django_ledger:entity-list')

    def get_queryset(self):
        return EntityModel.objects.for_user(user_model=self.request.user)


class EntityDeleteView(DeleteView):
    slug_url_kwarg = 'entity_slug'
    context_object_name = 'entity'
    template_name = 'django_ledger/entity_delete.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = _('Delete Entity ') + self.object.name
        context['header_title'] = context['page_title']
        return context

    def get_queryset(self):
        return EntityModel.objects.for_user(
            user_model=self.request.user
        )

    def get_success_url(self):
        return reverse('django_ledger:home')


# DASHBOARD VIEWS START ----
class EntityDashboardView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        loc_date = localdate()
        return reverse('django_ledger:entity-dashboard-month',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'year': loc_date.year,
                           'month': loc_date.month,
                       })


class FiscalYearEntityModelDashboardView(YearlyReportMixIn, FromToDatesMixIn, DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/entity_dashboard.html'
    DJL_NO_FROM_DATE_RAISE_404 = False
    DJL_NO_TO_DATE_RAISE_404 = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entity_model = self.object
        context['page_title'] = entity_model.name
        context['header_title'] = entity_model.name
        context['header_subtitle'] = _('Dashboard')
        context['header_subtitle_icon'] = 'mdi:monitor-dashboard'

        context['pnl_chart_id'] = f'djl-entity-pnl-chart-{randint(10000, 99999)}'
        context['pnl_chart_endpoint'] = reverse('django_ledger:entity-json-pnl',
                                                kwargs={
                                                    'entity_slug': self.kwargs['entity_slug']
                                                })
        context['payables_chart_id'] = f'djl-entity-payables-chart-{randint(10000, 99999)}'
        context['payables_chart_endpoint'] = reverse('django_ledger:entity-json-net-payables',
                                                     kwargs={
                                                         'entity_slug': self.kwargs['entity_slug']
                                                     })
        context['receivables_chart_id'] = f'djl-entity-receivables-chart-{randint(10000, 99999)}'
        context['receivables_chart_endpoint'] = reverse('django_ledger:entity-json-net-receivables',
                                                        kwargs={
                                                            'entity_slug': self.kwargs['entity_slug']
                                                        })

        context['from_date'] = self.get_from_date()
        context['to_date'] = self.get_to_date()
        set_default_entity(self.request, entity_model)
        context = self.get_entity_digest(context)

        # Unpaid Bills for Dashboard
        context['bills'] = self.get_unpaid_bills_qs()

        # Unpaid Invoices for Dashboard
        context['invoices'] = self.get_unpaid_invoices_qs()
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(
            user_model=self.request.user).select_related('coa')

    def get_digest_end_date(self):
        return self.get_year_end_date()

    def get_digest_start_date(self):
        return self.get_year_start_date()

    # def get_digest_end_date(self):
    #     return get_end_date_from_session(entity_slug=self.object.slug, request=self.request)

    def get_entity_digest(self, context, end_date=None):
        by_period = self.request.GET.get('by_period')
        entity_model = self.object
        if not end_date:
            end_date = self.get_digest_end_date()
        digest = entity_model.digest(user_model=self.request.user,
                                     to_date=end_date,
                                     by_period=True if by_period else False,
                                     process_ratios=True,
                                     process_roles=True,
                                     process_groups=True)
        context.update(digest)
        context['date_filter'] = end_date
        return context

    def get_unpaid_invoices_qs(self):
        return InvoiceModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).filter(
            Q(date__gte=self.get_digest_start_date()) &
            Q(date__lte=self.get_digest_end_date())
        ).select_related('customer').order_by('due_date')

    def get_unpaid_bills_qs(self):
        return BillModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).filter(
            Q(date__gte=self.get_digest_start_date()) &
            Q(date__lte=self.get_digest_end_date())
        ).select_related('vendor').order_by('due_date')


class QuarterlyEntityDashboardView(QuarterlyReportMixIn, FiscalYearEntityModelDashboardView):

    def get_digest_end_date(self):
        return self.get_quarter_end_date()

    def get_digest_start_date(self):
        return self.get_quarter_start_date()


class MonthlyEntityDashboardView(MonthlyReportMixIn, FiscalYearEntityModelDashboardView):
    def get_digest_end_date(self):
        return self.get_month_end_date()

    def get_digest_start_date(self):
        return self.get_month_start_date()


class DateEntityDashboardView(DateReportMixIn, MonthlyEntityDashboardView):
    pass


class FiscalYearEntityModelBalanceSheetView(YearlyReportMixIn, DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/balance_sheet.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Balance Sheet') + ': ' + self.object.name
        context['header_title'] = context['page_title']
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user_model=self.request.user)


class QuarterlyEntityModelBalanceSheetView(QuarterlyReportMixIn, FiscalYearEntityModelBalanceSheetView):
    """
    Quarter Balance Sheet View.
    """


class MonthlyEntityModelBalanceSheetView(MonthlyReportMixIn, FiscalYearEntityModelBalanceSheetView):
    """
    Monthly Balance Sheet View.
    """


class FiscalYearEntityModelIncomeStatementView(YearlyReportMixIn, DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/income_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Income Statement: ') + self.object.name
        context['header_title'] = _('Income Statement: ') + self.object.name
        return context

    def get_queryset(self):
        return EntityModel.objects.for_user(user_model=self.request.user)


class QuarterlyEntityModelIncomeStatementView(QuarterlyReportMixIn, FiscalYearEntityModelIncomeStatementView):
    """
    Quarter Income Statement View.
    """


class MonthlyEntityModelIncomeStatementView(MonthlyReportMixIn, FiscalYearEntityModelIncomeStatementView):
    """
    Monthly Income Statement View.
    """


# ENTITY MISC VIEWS ---
class SetDefaultEntityView(RedirectView):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        form = EntityFilterForm(request.POST, user_model=request.user)
        session_key = get_default_entity_session_key()
        if form.is_valid():
            entity_model = form.cleaned_data['entity_model']
            self.url = reverse('django_ledger:entity-dashboard',
                               kwargs={
                                   'entity_slug': entity_model.slug
                               })
            set_default_entity(request, entity_model)
        else:
            try:
                del self.request.session[session_key]
            finally:
                self.url = reverse('django_ledger:entity-list')
        return super().post(request, *args, **kwargs)


class SetSessionDate(RedirectView):
    """
    Sets the date filter on the session for a given entity.
    """
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        entity_slug = kwargs['entity_slug']
        as_of_form = AsOfDateFilterForm(data=request.POST, form_id=None)
        next_url = request.GET['next']

        if as_of_form.is_valid():
            as_of_form.clean()
            end_date = as_of_form.cleaned_data['date']
            set_end_date_filter(request, entity_slug, end_date)
        self.url = next_url
        return super().post(request, *args, **kwargs)


class GenerateSampleData(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            generate_sample_data(
                entity=self.kwargs['entity_slug'],
                user_model=self.request.user,
                start_dt=localtime() - timedelta(days=30 * 6),
                days_fw=30 * 9,
                tx_quantity=50
            )
        return super().get(request, *args, **kwargs)
