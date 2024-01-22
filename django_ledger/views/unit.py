from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DetailView, RedirectView

from django_ledger.forms.unit import EntityUnitModelCreateForm, EntityUnitModelUpdateForm
from django_ledger.io.io_core import get_localdate
from django_ledger.models import EntityUnitModel, EntityModel
from django_ledger.views.financial_statement import FiscalYearIncomeStatementView
from django_ledger.views.mixins import (DjangoLedgerSecurityMixIn, QuarterlyReportMixIn, MonthlyReportMixIn,
                                        DateReportMixIn, BaseDateNavigationUrlMixIn, EntityUnitMixIn, YearlyReportMixIn,
                                        PDFReportMixIn)


class EntityUnitModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = EntityUnitModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).select_related('entity')
        return super().get_queryset()


class EntityUnitModelListView(DjangoLedgerSecurityMixIn, EntityUnitModelModelViewQuerySetMixIn, ListView):
    template_name = 'django_ledger/unit/unit_list.html'
    PAGE_TITLE = _('Entity Unit List')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        # 'header_subtitle_icon': 'dashicons:businesswoman'
    }
    context_object_name = 'unit_list'


class EntityUnitModelDetailView(DjangoLedgerSecurityMixIn, EntityUnitModelModelViewQuerySetMixIn, DetailView):
    template_name = 'django_ledger/unit/unit_detail.html'
    PAGE_TITLE = _('Entity Unit Detail')
    slug_url_kwarg = 'unit_slug'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        # 'header_subtitle_icon': 'dashicons:businesswoman'
    }
    context_object_name = 'unit'


class EntityUnitModelCreateView(DjangoLedgerSecurityMixIn, EntityUnitModelModelViewQuerySetMixIn, CreateView):
    template_name = 'django_ledger/unit/unit_create.html'
    PAGE_TITLE = _('Entity Unit Create')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        # 'header_subtitle_icon': 'dashicons:businesswoman'
    }

    def get_form(self, form_class=None):
        return EntityUnitModelCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:unit-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def form_valid(self, form):
        entity_unit_model: EntityUnitModel = form.save(commit=False)
        entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user)
        entity_model = get_object_or_404(entity_model_qs, slug__exact=self.kwargs['entity_slug'])
        entity_unit_model.entity = entity_model
        EntityUnitModel.add_root(instance=entity_unit_model)
        return HttpResponseRedirect(self.get_success_url())


class EntityUnitUpdateView(DjangoLedgerSecurityMixIn, EntityUnitModelModelViewQuerySetMixIn, UpdateView):
    template_name = 'django_ledger/unit/unit_update.html'
    PAGE_TITLE = _('Entity Unit Update')
    slug_url_kwarg = 'unit_slug'
    context_object_name = 'unit'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        # 'header_subtitle_icon': 'dashicons:businesswoman'
    }

    def get_form(self, form_class=None):
        return EntityUnitModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:unit-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def form_valid(self, form):
        instance: EntityUnitModel = form.save(commit=False)
        instance.clean()
        form.save()
        return super().form_valid(form=form)


# Financial Statements...


# BALANCE SHEET.....
class BaseEntityUnitModelBalanceSheetView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse('django_ledger:unit-bs-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'unit_slug': self.kwargs['unit_slug'],
                           'year': year
                       })


class FiscalYearEntityUnitModelBalanceSheetView(DjangoLedgerSecurityMixIn,
                                                EntityUnitModelModelViewQuerySetMixIn,
                                                BaseDateNavigationUrlMixIn,
                                                EntityUnitMixIn,
                                                YearlyReportMixIn,
                                                PDFReportMixIn,
                                                DetailView):
    """
    Entity Unit Fiscal Year Balance Sheet View Class
    """

    context_object_name = 'unit_model'
    slug_url_kwarg = 'unit_slug'
    template_name = 'django_ledger/financial_statements/balance_sheet.html'
    pdf_report_type = 'BS'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entity_model'] = self.object.entity
        return context


class QuarterlyEntityUnitModelBalanceSheetView(FiscalYearEntityUnitModelBalanceSheetView, QuarterlyReportMixIn):
    """
    Entity Unit Fiscal Quarter Balance Sheet View Class.
    """


class MonthlyEntityUnitModelBalanceSheetView(FiscalYearEntityUnitModelBalanceSheetView, MonthlyReportMixIn):
    """
    Entity Unit Fiscal Month Balance Sheet View Class.
    """


class DateEntityUnitModelBalanceSheetView(MonthlyEntityUnitModelBalanceSheetView, DateReportMixIn):
    """
    Entity Unit Date Balance Sheet View Class.
    """


# INCOME STATEMENT....
class BaseEntityUnitModelIncomeStatementView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse('django_ledger:unit-ic-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'unit_slug': self.kwargs['unit_slug'],
                           'year': year
                       })


class FiscalYearEntityUnitModelIncomeStatementView(DjangoLedgerSecurityMixIn,
                                                   EntityUnitModelModelViewQuerySetMixIn,
                                                   BaseDateNavigationUrlMixIn,
                                                   EntityUnitMixIn,
                                                   YearlyReportMixIn,
                                                   PDFReportMixIn,
                                                   DetailView):
    context_object_name = 'unit_model'
    slug_url_kwarg = 'unit_slug'
    template_name = 'django_ledger/financial_statements/income_statement.html'
    pdf_report_type = 'IS'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entity_model'] = self.object.entity
        return context


class QuarterlyIncomeStatementView(FiscalYearIncomeStatementView, QuarterlyReportMixIn):
    """
    Entity Unit Fiscal Quarter Income Statement View Class
    """


class MonthlyIncomeStatementView(FiscalYearIncomeStatementView, MonthlyReportMixIn):
    """
    Entity Unit Fiscal Month Income Statement View Class
    """


class DateIncomeStatementView(FiscalYearIncomeStatementView, DateReportMixIn):
    """
    Entity Unit Date Income Statement View Class
    """


# CASHFLOW STATEMENT
class BaseEntityUnitModelCashFlowStatementView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse('django_ledger:unit-cf-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'unit_slug': self.kwargs['unit_slug'],
                           'year': year
                       })


class FiscalYearEntityUnitModelCashFlowStatementView(DjangoLedgerSecurityMixIn,
                                                     EntityUnitModelModelViewQuerySetMixIn,
                                                     BaseDateNavigationUrlMixIn,
                                                     EntityUnitMixIn,
                                                     YearlyReportMixIn,
                                                     PDFReportMixIn,
                                                     DetailView):
    context_object_name = 'unit_model'
    slug_url_kwarg = 'unit_slug'
    template_name = 'django_ledger/financial_statements/cash_flow.html'
    pdf_report_type = 'CFS'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entity_model'] = self.object.entity
        return context


class QuarterlyEntityUnitModelCashFlowStatementView(FiscalYearEntityUnitModelCashFlowStatementView,
                                                    QuarterlyReportMixIn):
    """
    Entity Unit Fiscal Quarter Cash Flow Statement View Class
    """


class MonthlyEntityUnitModelCashFlowStatementView(FiscalYearEntityUnitModelCashFlowStatementView,
                                                  MonthlyReportMixIn):
    """
    Entity Unit Fiscal Month Cash Flow Statement View Class
    """


class DateEntityUnitModelCashFlowStatementView(FiscalYearEntityUnitModelCashFlowStatementView,
                                               DateReportMixIn):
    """
    Entity Unit Date Cash Flow Statement View Class
    """
