"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import timedelta
from random import randint

from django.contrib.messages import add_message, ERROR
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localtime, localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView, DeleteView

from django_ledger.forms.app_filters import AsOfDateFilterForm, EntityFilterForm
from django_ledger.forms.entity import EntityModelUpdateForm, EntityModelCreateForm
from django_ledger.io.data_generator import EntityDataGenerator
from django_ledger.models import (EntityModel, EntityUnitModel, ItemThroughModel, TransactionModel,
                                  JournalEntryModel, PurchaseOrderModel, BillModel, InvoiceModel)
from django_ledger.utils import (
    get_default_entity_session_key,
    populate_default_coa, set_default_entity,
    set_session_date_filter
)
from django_ledger.views.mixins import (
    QuarterlyReportMixIn, YearlyReportMixIn,
    MonthlyReportMixIn, DateReportMixIn, LoginRequiredMixIn, SessionConfigurationMixIn, EntityUnitMixIn,
    EntityDigestMixIn, UnpaidElementsMixIn, BaseDateNavigationUrlMixIn
)


# Entity CRUD Views ----
class EntityModelListView(LoginRequiredMixIn, ListView):
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


class EntityModelCreateView(LoginRequiredMixIn, CreateView):
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
        entity_model = form.save()
        default_coa = form.cleaned_data.get('default_coa')
        activate_accounts = form.cleaned_data.get('activate_all_accounts')
        if default_coa:
            populate_default_coa(entity_model=entity_model, activate_accounts=activate_accounts)

        sample_data = form.cleaned_data.get('generate_sample_data')
        if sample_data:
            entity_generator = EntityDataGenerator(
                entity_model=entity_model,
                user_model=self.request.user,
                start_date=localtime() - timedelta(days=30 * 8),
                capital_contribution=50000,
                days_forward=30 * 9,
                tx_quantity=50
            )
            entity_generator.populate_entity()

        self.object = entity_model
        return super().form_valid(form)


class EntityModelUpdateView(LoginRequiredMixIn, UpdateView):
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


class EntityDeleteView(LoginRequiredMixIn, DeleteView):
    slug_url_kwarg = 'entity_slug'
    context_object_name = 'entity'
    template_name = 'django_ledger/entity_delete.html'
    verify_descendants = False

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

    def delete(self, request, *args, **kwargs):
        entity_model: EntityModel = self.get_object()

        # todo: this will need to be changed once hierarchical support is enabled.
        if self.verify_descendants:
            c = entity_model.children.count()
            if c != 0:
                add_message(request,
                            level=ERROR,
                            extra_tags='is-danger',
                            message=_('Entity has %s children. Must delete children first.' % c))
                return self.get(request, *args, **kwargs)

        ItemThroughModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).all().delete()

        PurchaseOrderModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).all().delete()

        BillModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).all().delete()

        InvoiceModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).all().delete()

        TransactionModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).all().delete()

        JournalEntryModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).all().delete()

        # entity_model.entityunitmodel_set.all().delete()
        entity_model.ledgermodel_set.all().delete()
        entity_model.items.all().delete()
        return super().delete(request, *args, **kwargs)


# DASHBOARD VIEWS START ----
class EntityModelDetailView(LoginRequiredMixIn,
                            EntityUnitMixIn,
                            RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        loc_date = localdate()
        unit_slug = self.get_unit_slug()
        if unit_slug:
            return reverse('django_ledger:unit-dashboard-month',
                           kwargs={
                               'entity_slug': self.kwargs['entity_slug'],
                               'unit_slug': unit_slug,
                               'year': loc_date.year,
                               'month': loc_date.month,
                           })
        return reverse('django_ledger:entity-dashboard-month',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'year': loc_date.year,
                           'month': loc_date.month,
                       })


class FiscalYearEntityModelDashboardView(LoginRequiredMixIn,
                                         SessionConfigurationMixIn,
                                         BaseDateNavigationUrlMixIn,
                                         UnpaidElementsMixIn,
                                         EntityUnitMixIn,
                                         EntityDigestMixIn,
                                         YearlyReportMixIn,
                                         DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/entity_dashboard.html'
    DJL_NO_FROM_DATE_RAISE_404 = False
    DJL_NO_TO_DATE_RAISE_404 = False

    FETCH_UNPAID_BILLS = True
    FETCH_UNPAID_INVOICES = True

    def get_context_data(self, **kwargs):
        context = super(FiscalYearEntityModelDashboardView, self).get_context_data(**kwargs)
        entity_model: EntityModel = self.object
        context['page_title'] = entity_model.name
        context['header_title'] = entity_model.name
        context['header_subtitle'] = _('Dashboard')
        context['header_subtitle_icon'] = 'mdi:monitor-dashboard'

        unit_slug = context.get('unit_slug', self.get_unit_slug())
        KWARGS = dict(entity_slug=self.kwargs['entity_slug'])

        if unit_slug:
            KWARGS['unit_slug'] = unit_slug

        url_pointer = 'entity' if not unit_slug else 'unit'
        context['pnl_chart_id'] = f'djl-entity-pnl-chart-{randint(10000, 99999)}'
        context['pnl_chart_endpoint'] = reverse(f'django_ledger:{url_pointer}-json-pnl',
                                                kwargs=KWARGS)
        context['payables_chart_id'] = f'djl-entity-payables-chart-{randint(10000, 99999)}'
        context['payables_chart_endpoint'] = reverse(f'django_ledger:{url_pointer}-json-net-payables',
                                                     kwargs=KWARGS)
        context['receivables_chart_id'] = f'djl-entity-receivables-chart-{randint(10000, 99999)}'
        context['receivables_chart_endpoint'] = reverse(f'django_ledger:{url_pointer}-json-net-receivables',
                                                        kwargs=KWARGS)

        context = self.get_entity_digest(context)

        return context

    def get_fy_start_month(self) -> int:
        entity_model: EntityModel = self.object
        return entity_model.fy_start_month

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(
            user_model=self.request.user).select_related('coa')


class QuarterlyEntityDashboardView(FiscalYearEntityModelDashboardView, QuarterlyReportMixIn):
    """
    Entity Quarterly Dashboard View.
    """


class MonthlyEntityDashboardView(FiscalYearEntityModelDashboardView, MonthlyReportMixIn):
    """
    Monthly Entity Dashboard View.
    """


class DateEntityDashboardView(FiscalYearEntityModelDashboardView, DateReportMixIn):
    """
    Date-specific Entity Dashboard View.
    """


# BALANCE SHEET -----------
class EntityModelBalanceSheetView(LoginRequiredMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:entity-bs-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'year': year
                       })


class FiscalYearEntityModelBalanceSheetView(LoginRequiredMixIn,
                                            SessionConfigurationMixIn,
                                            BaseDateNavigationUrlMixIn,
                                            EntityUnitMixIn,
                                            YearlyReportMixIn,
                                            DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/balance_sheet.html'

    def get_context_data(self, **kwargs):
        context = super(FiscalYearEntityModelBalanceSheetView, self).get_context_data(**kwargs)
        context['page_title'] = _('Balance Sheet') + ': ' + self.object.name
        context['header_title'] = context['page_title']
        unit_slug = self.request.GET.get('unit')
        if unit_slug:
            context['unit_model'] = get_object_or_404(EntityUnitModel,
                                                      slug=unit_slug,
                                                      entity__slug__exact=self.kwargs['entity_slug'])
        return context

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        return EntityModel.objects.for_user(user_model=self.request.user)

    def get_fy_start_month(self) -> int:
        entity_model: EntityModel = self.object
        return entity_model.fy_start_month


class QuarterlyEntityModelBalanceSheetView(QuarterlyReportMixIn, FiscalYearEntityModelBalanceSheetView):
    """
    Quarter Balance Sheet View.
    """


class MonthlyEntityModelBalanceSheetView(MonthlyReportMixIn, FiscalYearEntityModelBalanceSheetView):
    """
    Monthly Balance Sheet View.
    """


class DateEntityModelBalanceSheetView(DateReportMixIn, FiscalYearEntityModelBalanceSheetView):
    """
    Date Balance Sheet View.
    """


# INCOME STATEMENT ------------
class EntityModelIncomeStatementView(LoginRequiredMixIn, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:entity-ic-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'year': year
                       })


class FiscalYearEntityModelIncomeStatementView(LoginRequiredMixIn,
                                               SessionConfigurationMixIn,
                                               BaseDateNavigationUrlMixIn,
                                               EntityUnitMixIn,
                                               YearlyReportMixIn,
                                               DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/income_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Income Statement: ') + self.object.name
        context['header_title'] = _('Income Statement: ') + self.object.name
        unit_slug = self.kwargs.get('unit_slug')
        if unit_slug:
            context['unit_model'] = get_object_or_404(EntityUnitModel,
                                                      slug__exact=unit_slug,
                                                      entity__slug__exact=self.kwargs['entity_slug'])
        return context

    def get_queryset(self):
        return EntityModel.objects.for_user(user_model=self.request.user)

    def get_fy_start_month(self) -> int:
        entity_model: EntityModel = self.object
        return entity_model.fy_start_month


class QuarterlyEntityModelIncomeStatementView(QuarterlyReportMixIn, FiscalYearEntityModelIncomeStatementView):
    """
    Quarter Income Statement View.
    """


class MonthlyEntityModelIncomeStatementView(MonthlyReportMixIn, FiscalYearEntityModelIncomeStatementView):
    """
    Monthly Income Statement View.
    """


class DateModelIncomeStatementView(DateReportMixIn, FiscalYearEntityModelIncomeStatementView):
    """
    Date Income Statement View.
    """


# ENTITY MISC VIEWS ---
class SetDefaultEntityView(LoginRequiredMixIn, RedirectView):
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


class SetSessionDate(LoginRequiredMixIn, RedirectView):
    """
    Sets the date filter on the session for a given entity.
    """
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        entity_slug = kwargs['entity_slug']
        as_of_form = AsOfDateFilterForm(data=request.POST, form_id=None)
        # next_url = request.GET['next']

        if as_of_form.is_valid():
            as_of_form.clean()
            end_date = as_of_form.cleaned_data['date']
            set_session_date_filter(request, entity_slug, end_date)
            self.url = reverse('django_ledger:entity-dashboard-date',
                               kwargs={
                                   'entity_slug': self.kwargs['entity_slug'],
                                   'year': end_date.year,
                                   'month': end_date.month,
                                   'day': end_date.day,
                               })
        return super().post(request, *args, **kwargs)

# class GenerateSampleData(LoginRequiredMixIn, RedirectView):
#
#     def get_redirect_url(self, *args, **kwargs):
#         return reverse('django_ledger:entity-dashboard',
#                        kwargs={
#                            'entity_slug': self.kwargs['entity_slug']
#                        })
#
#     def get(self, request, *args, **kwargs):
#         if request.user.is_authenticated:
#             generate_sample_data(
#                 entity_model=self.kwargs['entity_slug'],
#                 user_model=self.request.user,
#                 start_dt=localtime() - timedelta(days=30 * 6),
#                 days_fw=30 * 9,
#                 tx_quantity=5
#             )
#         return super().get(request, *args, **kwargs)
