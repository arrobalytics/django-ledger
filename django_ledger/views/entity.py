"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from datetime import timedelta
from decimal import Decimal
from random import randint

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView, DeleteView

from django_ledger.forms.entity import EntityModelUpdateForm, EntityModelCreateForm
from django_ledger.io.data_generator import EntityDataGenerator
from django_ledger.models import (EntityModel, EntityUnitModel, ItemTransactionModel, TransactionModel)
from django_ledger.views.mixins import (
    QuarterlyReportMixIn, YearlyReportMixIn,
    MonthlyReportMixIn, DateReportMixIn, DjangoLedgerSecurityMixIn, EntityUnitMixIn,
    EntityDigestMixIn, UnpaidElementsMixIn, BaseDateNavigationUrlMixIn
)


class EntityModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        return EntityModel.objects.for_user(user_model=self.request.user).select_related('default_coa')


# Entity CRUD Views ----
class EntityModelListView(DjangoLedgerSecurityMixIn, EntityModelModelViewQuerySetMixIn, ListView):
    template_name = 'django_ledger/entity/entitiy_list.html'
    context_object_name = 'entities'
    PAGE_TITLE = _('My Entities')
    extra_context = {
        'header_title': PAGE_TITLE,
        'page_title': PAGE_TITLE
    }


class EntityModelCreateView(DjangoLedgerSecurityMixIn, EntityModelModelViewQuerySetMixIn, CreateView):
    template_name = 'django_ledger/entity/entity_create.html'
    form_class = EntityModelCreateForm
    PAGE_TITLE = _('Create Entity')
    extra_context = {
        'header_title': PAGE_TITLE,
        'page_title': PAGE_TITLE
    }

    def get_success_url(self):
        return reverse('django_ledger:home')

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        default_coa = cleaned_data.get('default_coa')
        activate_accounts = cleaned_data.get('activate_all_accounts')
        sample_data = form.cleaned_data.get('generate_sample_data')

        user_model = self.request.user

        entity_model: EntityModel = EntityModel(
            name=cleaned_data['name'],
            slug=EntityModel.generate_slug_from_name(name=cleaned_data['name']),
            address_1=cleaned_data['address_1'],
            address_2=cleaned_data['address_2'],
            city=cleaned_data['city'],
            state=cleaned_data['state'],
            zip_code=cleaned_data['zip_code'],
            country=cleaned_data['country'],
            email=cleaned_data['email'],
            website=cleaned_data['website'],
            phone=cleaned_data['phone'],
            fy_start_month=cleaned_data['fy_start_month'],
            accrual_method=cleaned_data['accrual_method'],
            admin=user_model
        )
        entity_model: EntityModel = EntityModel.add_root(instance=entity_model)
        default_coa_model = entity_model.create_chart_of_accounts(assign_as_default=True, commit=True)

        if default_coa:
            entity_model.populate_default_coa(activate_accounts=activate_accounts,
                                              coa_model=default_coa_model)

        if sample_data:
            entity_generator = EntityDataGenerator(
                entity_model=entity_model,
                user_model=self.request.user,
                start_date=localdate() - timedelta(days=30 * 8),
                capital_contribution=Decimal.from_float(50000),
                days_forward=30 * 7,
                tx_quantity=cleaned_data['tx_quantity']
            )
            entity_generator.populate_entity()

        return HttpResponseRedirect(
            redirect_to=self.get_success_url()
        )


class EntityModelUpdateView(DjangoLedgerSecurityMixIn, EntityModelModelViewQuerySetMixIn, UpdateView):
    context_object_name = 'entity'
    template_name = 'django_ledger/entity/entity_update.html'
    form_class = EntityModelUpdateForm
    slug_url_kwarg = 'entity_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        context['header_title'] = self.object.name
        return context

    def get_success_url(self):
        return reverse('django_ledger:entity-list')


class EntityDeleteView(DjangoLedgerSecurityMixIn, EntityModelModelViewQuerySetMixIn, DeleteView):
    slug_url_kwarg = 'entity_slug'
    context_object_name = 'entity'
    template_name = 'django_ledger/entity/entity_delete.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['page_title'] = _('Delete Entity ') + self.object.name
        context['header_title'] = context['page_title']
        return context

    def get_success_url(self):
        return reverse('django_ledger:home')

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        entity_model: EntityModel = self.get_object()
        entity_model.default_coa = None
        entity_model.save(update_fields=['default_coa'])

        ItemTransactionModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).delete()

        TransactionModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        ).delete()

        return super().delete(request, *args, **kwargs)


# DASHBOARD VIEWS START ----
class EntityModelDetailView(DjangoLedgerSecurityMixIn,
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


class FiscalYearEntityModelDashboardView(DjangoLedgerSecurityMixIn,
                                         EntityModelModelViewQuerySetMixIn,
                                         BaseDateNavigationUrlMixIn,
                                         UnpaidElementsMixIn,
                                         EntityUnitMixIn,
                                         EntityDigestMixIn,
                                         YearlyReportMixIn,
                                         DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/entity/entity_dashboard.html'
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
class EntityModelBalanceSheetRedirectView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:entity-bs-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'year': year
                       })


class FiscalYearEntityModelBalanceSheetView(DjangoLedgerSecurityMixIn,
                                            EntityModelModelViewQuerySetMixIn,
                                            BaseDateNavigationUrlMixIn,
                                            EntityUnitMixIn,
                                            YearlyReportMixIn,
                                            DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/financial_statements/balance_sheet.html'

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
class EntityModelIncomeStatementRedirectView(DjangoLedgerSecurityMixIn, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:entity-ic-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'year': year
                       })


class FiscalYearEntityModelIncomeStatementView(DjangoLedgerSecurityMixIn,
                                               EntityModelModelViewQuerySetMixIn,
                                               BaseDateNavigationUrlMixIn,
                                               EntityUnitMixIn,
                                               YearlyReportMixIn,
                                               DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/financial_statements/income_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entity_model: EntityModel = self.object
        context['page_title'] = _('Income Statement: ') + entity_model.name
        context['header_title'] = _('Income Statement: ') + entity_model.name
        unit_slug = self.kwargs.get('unit_slug')
        if unit_slug:
            entity_unit_qs = entity_model.entityunitmodel_set.all()
            context['unit_model'] = get_object_or_404(entity_unit_qs,
                                                      slug__exact=unit_slug,
                                                      entity__slug__exact=self.kwargs['entity_slug'])
        return context


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


# CASH FLOW STATEMENT ----
class EntityModelCashFlowStatementRedirectView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:entity-cf-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'year': year
                       })


class FiscalYearEntityModelCashFlowStatementView(DjangoLedgerSecurityMixIn,
                                                 EntityModelModelViewQuerySetMixIn,
                                                 BaseDateNavigationUrlMixIn,
                                                 EntityUnitMixIn,
                                                 YearlyReportMixIn,
                                                 DetailView):
    """
    Fiscal Year Cash Flow Statement View.
    """

    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/financial_statements/cash_flow.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entity_model: EntityModel = self.object
        context['page_title'] = _('Cash Flow Statement: ') + entity_model.name
        context['header_title'] = _('Cash Flow Statement: ') + entity_model.name
        unit_slug = self.kwargs.get('unit_slug')
        if unit_slug:
            entity_unit_qs = entity_model.entityunitmodel_set.all()
            context['unit_model'] = get_object_or_404(entity_unit_qs,
                                                      slug__exact=unit_slug,
                                                      entity__slug__exact=self.kwargs['entity_slug'])
        return context


class QuarterlyEntityModelCashFlowStatementView(QuarterlyReportMixIn, FiscalYearEntityModelCashFlowStatementView):
    """
    Quarter Cash Flow Statement View.
    """


class MonthlyEntityModelCashFlowStatementView(MonthlyReportMixIn, FiscalYearEntityModelCashFlowStatementView):
    """
    Monthly Cash Flow Statement View.
    """


class DateEntityModelCashFlowStatementView(DateReportMixIn, FiscalYearEntityModelCashFlowStatementView):
    """
    Date Cash Flow Statement View.
    """
