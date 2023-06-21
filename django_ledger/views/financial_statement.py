"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView

from django_ledger.models import EntityModel, EntityUnitModel
from django_ledger.views.mixins import (
    QuarterlyReportMixIn, YearlyReportMixIn,
    MonthlyReportMixIn, DateReportMixIn, DjangoLedgerSecurityMixIn, EntityUnitMixIn,
    BaseDateNavigationUrlMixIn, PDFReportMixIn
)


class EntityModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        return EntityModel.objects.for_user(
            user_model=self.request.user).select_related('default_coa')


# BALANCE SHEET -----------
class BaseBalanceSheetRedirectView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:entity-bs-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'year': year
                       })


class FiscalYearBalanceSheetView(DjangoLedgerSecurityMixIn,
                                 EntityModelModelViewQuerySetMixIn,
                                 BaseDateNavigationUrlMixIn,
                                 EntityUnitMixIn,
                                 YearlyReportMixIn,
                                 PDFReportMixIn,
                                 DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/financial_statements/balance_sheet.html'
    pdf_report_type = 'BS'

    def get_context_data(self, **kwargs):
        context = super(FiscalYearBalanceSheetView, self).get_context_data(**kwargs)
        context['page_title'] = _('Balance Sheet') + ': ' + self.object.name
        context['header_title'] = context['page_title']
        unit_slug = self.request.GET.get('unit')
        if unit_slug:
            context['unit_model'] = get_object_or_404(EntityUnitModel,
                                                      slug=unit_slug,
                                                      entity__slug__exact=self.kwargs['entity_slug'])
        return context


class QuarterlyBalanceSheetView(FiscalYearBalanceSheetView, QuarterlyReportMixIn):
    """
    Quarter Balance Sheet View.
    """


class MonthlyBalanceSheetView(FiscalYearBalanceSheetView, MonthlyReportMixIn):
    """
    Monthly Balance Sheet View.
    """


class DateBalanceSheetView(FiscalYearBalanceSheetView, DateReportMixIn):
    """
    Date Balance Sheet View.
    """


# INCOME STATEMENT ------------
class BaseIncomeStatementRedirectView(DjangoLedgerSecurityMixIn, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:entity-ic-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'year': year
                       })


class FiscalYearIncomeStatementView(DjangoLedgerSecurityMixIn,
                                    EntityModelModelViewQuerySetMixIn,
                                    BaseDateNavigationUrlMixIn,
                                    EntityUnitMixIn,
                                    YearlyReportMixIn,
                                    PDFReportMixIn,
                                    DetailView):
    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/financial_statements/income_statement.html'
    pdf_report_type = 'IS'

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


class QuarterlyIncomeStatementView(FiscalYearIncomeStatementView, QuarterlyReportMixIn):
    """
    Quarter Income Statement View.
    """


class MonthlyIncomeStatementView(FiscalYearIncomeStatementView, MonthlyReportMixIn):
    """
    Monthly Income Statement View.
    """


class DateModelIncomeStatementView(FiscalYearIncomeStatementView, DateReportMixIn):
    """
    Date Income Statement View.
    """


# CASH FLOW STATEMENT ----
class BaseCashFlowStatementRedirectView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:entity-cf-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'year': year
                       })


class FiscalYearCashFlowStatementView(DjangoLedgerSecurityMixIn,
                                      EntityModelModelViewQuerySetMixIn,
                                      BaseDateNavigationUrlMixIn,
                                      EntityUnitMixIn,
                                      YearlyReportMixIn,
                                      PDFReportMixIn,
                                      DetailView):
    """
    Fiscal Year Cash Flow Statement View.
    """

    context_object_name = 'entity'
    slug_url_kwarg = 'entity_slug'
    template_name = 'django_ledger/financial_statements/cash_flow.html'
    pdf_report_type = 'CFS'

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


class QuarterlyCashFlowStatementView(FiscalYearCashFlowStatementView, QuarterlyReportMixIn):
    """
    Quarter Cash Flow Statement View.
    """


class MonthlyCashFlowStatementView(FiscalYearCashFlowStatementView, MonthlyReportMixIn):
    """
    Monthly Cash Flow Statement View.
    """


class DateCashFlowStatementView(FiscalYearCashFlowStatementView, DateReportMixIn):
    """
    Date Cash Flow Statement View.
    """
