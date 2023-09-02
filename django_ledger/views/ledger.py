"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView

from django_ledger.forms.ledger import LedgerModelCreateForm, LedgerModelUpdateForm
from django_ledger.models.entity import EntityModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.views.mixins import (
    YearlyReportMixIn, QuarterlyReportMixIn,
    MonthlyReportMixIn, DjangoLedgerSecurityMixIn, DateReportMixIn, BaseDateNavigationUrlMixIn,
    EntityUnitMixIn, PDFReportMixIn)


class LedgerModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = LedgerModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).select_related('entity')
        return super().get_queryset()


class LedgerModelListView(DjangoLedgerSecurityMixIn, LedgerModelModelViewQuerySetMixIn, ListView):
    context_object_name = 'ledgers'
    template_name = 'django_ledger/ledger/ledger_list.html'
    PAGE_TITLE = _('Entity Ledgers')
    show_hidden = False
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if self.show_hidden:
            return qs.hidden()
        return qs.visible()


class LedgerModelCreateView(DjangoLedgerSecurityMixIn, LedgerModelModelViewQuerySetMixIn, CreateView):
    template_name = 'django_ledger/ledger/ledger_create.html'
    PAGE_TITLE = _('Create Ledger')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_form(self, form_class=None):
        return LedgerModelCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        entity = EntityModel.objects.for_user(
            user_model=self.request.user).get(slug__exact=self.kwargs['entity_slug'])
        instance = form.save(commit=False)
        instance.entity = entity
        self.object = form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


class LedgerModelUpdateView(DjangoLedgerSecurityMixIn, LedgerModelModelViewQuerySetMixIn, UpdateView):
    context_object_name = 'ledger'
    pk_url_kwarg = 'ledger_pk'
    template_name = 'django_ledger/ledger/ledger_update.html'

    def get_form(self, form_class=None):
        return LedgerModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Update Ledger: ') + self.object.name
        context['header_title'] = context['page_title']
        return context

    def get_success_url(self):
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


# Ledger Balance Sheet Views...
class BaseLedgerModelBalanceSheetView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:ledger-bs-year', kwargs={
            'entity_slug': self.kwargs['entity_slug'],
            'ledger_pk': self.kwargs['ledger_pk'],
            'year': year
        })


class FiscalYearLedgerModelBalanceSheetView(DjangoLedgerSecurityMixIn,
                                            LedgerModelModelViewQuerySetMixIn,
                                            BaseDateNavigationUrlMixIn,
                                            EntityUnitMixIn,
                                            YearlyReportMixIn,
                                            PDFReportMixIn,
                                            DetailView):
    context_object_name = 'ledger'
    pk_url_kwarg = 'ledger_pk'
    template_name = 'django_ledger/financial_statements/balance_sheet.html'
    pdf_report_type = 'BS'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Ledger Balance Sheet: ') + self.object.name
        context['header_title'] = context['page_title']
        return context


class QuarterlyLedgerModelBalanceSheetView(FiscalYearLedgerModelBalanceSheetView, QuarterlyReportMixIn):
    """
    Quarter Balance Sheet View.
    """


class MonthlyLedgerModelBalanceSheetView(FiscalYearLedgerModelBalanceSheetView, MonthlyReportMixIn):
    """
    Monthly Balance Sheet View.
    """


class DateLedgerModelBalanceSheetView(FiscalYearLedgerModelBalanceSheetView, DateReportMixIn):
    """
    Date Balance Sheet View.
    """


# Ledger Income Statement Views...
class BaseLedgerIncomeStatementView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:ledger-ic-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'ledger_pk': self.kwargs['ledger_pk'],
                           'year': year
                       })


class FiscalYearLedgerIncomeStatementView(DjangoLedgerSecurityMixIn,
                                          LedgerModelModelViewQuerySetMixIn,
                                          BaseDateNavigationUrlMixIn,
                                          EntityUnitMixIn,
                                          YearlyReportMixIn,
                                          PDFReportMixIn,
                                          DetailView):
    context_object_name = 'ledger'
    pk_url_kwarg = 'ledger_pk'
    template_name = 'django_ledger/financial_statements/income_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Ledger Income Statement: ') + self.object.name
        context['header_title'] = context['page_title']
        return context


class QuarterlyLedgerIncomeStatementView(FiscalYearLedgerIncomeStatementView, QuarterlyReportMixIn):
    """
    Quarterly Income Statement Quarter Report.
    """


class MonthlyLedgerIncomeStatementView(FiscalYearLedgerIncomeStatementView, MonthlyReportMixIn):
    """
    Monthly Income Statement Monthly Report.
    """


class DateLedgerIncomeStatementView(FiscalYearLedgerIncomeStatementView, DateReportMixIn):
    """
    Date Income Statement Monthly Report.
    """


# CASH FLOW STATEMENT ----
class BaseLedgerModelCashFlowStatementRedirectView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:ledger-cf-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'ledger_pk': self.kwargs['ledger_pk'],
                           'year': year
                       })


class FiscalYearLedgerModelCashFlowStatementView(DjangoLedgerSecurityMixIn,
                                                 LedgerModelModelViewQuerySetMixIn,
                                                 BaseDateNavigationUrlMixIn,
                                                 EntityUnitMixIn,
                                                 YearlyReportMixIn,
                                                 PDFReportMixIn,
                                                 DetailView):
    """
    Fiscal Year Cash Flow Statement View.
    """

    context_object_name = 'ledger'
    pk_url_kwarg = 'ledger_pk'
    template_name = 'django_ledger/financial_statements/cash_flow.html'
    pdf_report_type = 'CFS'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Ledger Cash Flow Statement: ') + self.object.name
        context['header_title'] = context['page_title']
        return context


class QuarterlyLedgerModelCashFlowStatementView(FiscalYearLedgerModelCashFlowStatementView, QuarterlyReportMixIn):
    """
    Quarter Cash Flow Statement View.
    """


class MonthlyLedgerModelCashFlowStatementView(FiscalYearLedgerModelCashFlowStatementView, MonthlyReportMixIn):
    """
    Monthly Cash Flow Statement View.
    """


class DateLedgerModelCashFlowStatementView(FiscalYearLedgerModelCashFlowStatementView, DateReportMixIn):
    """
    Date Cash Flow Statement View.
    """
