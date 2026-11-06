"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Financial statement views (RETRIEVE / report).

  * Balance Sheet  — FiscalYear / Quarterly / Monthly / Date
  * Income Statement — same period mixins
  * Cash Flow Statement — same period mixins

All reports require entity authorization and optionally support PDF export
via PDFReportMixIn. Querysets are user-scoped (for_user).
"""

from typing import Optional

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView

from django_ledger.io.io_core import get_localdate
from django_ledger.models import EntityModel, EntityUnitModel
from django_ledger.models.entity import EntityModelQuerySet
from django_ledger.views.mixins import (
    QuarterlyReportMixIn,
    YearlyReportMixIn,
    MonthlyReportMixIn,
    DateReportMixIn,
    DjangoLedgerSecurityMixIn,
    EntityUnitMixIn,
    BaseDateNavigationUrlMixIn,
    PDFReportMixIn,
)


class EntityModelModelBaseView(DjangoLedgerSecurityMixIn):
    """
    User-scoped entity queryset shared by all financial-statement report views.
    """

    queryset: Optional[EntityModelQuerySet] = None

    def get_queryset(self) -> EntityModelQuerySet:
        if self.queryset is None:
            qs: EntityModelQuerySet = EntityModel.objects.for_user(user_model=self.request.user).select_related(
                'default_coa'
            )
            self.queryset = qs
        return super().get_queryset()


# -----------------
# RETRIEVE — Balance Sheet
# -----------------
class BaseBalanceSheetRedirectView(DjangoLedgerSecurityMixIn, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse('django_ledger:entity-bs-year', kwargs={'entity_slug': self.kwargs['entity_slug'], 'year': year})


class FiscalYearBalanceSheetView(
    EntityModelModelBaseView,
    BaseDateNavigationUrlMixIn,
    EntityUnitMixIn,
    YearlyReportMixIn,
    PDFReportMixIn,
    DetailView,
):
    """Fiscal-year balance sheet for an authorized entity."""

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
            context['unit_model'] = get_object_or_404(
                EntityUnitModel, slug=unit_slug, entity__slug__exact=self.kwargs['entity_slug']
            )
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


# -----------------
# RETRIEVE — Income Statement
# -----------------
class BaseIncomeStatementRedirectView(DjangoLedgerSecurityMixIn, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse('django_ledger:entity-ic-year', kwargs={'entity_slug': self.kwargs['entity_slug'], 'year': year})


class FiscalYearIncomeStatementView(
    EntityModelModelBaseView,
    BaseDateNavigationUrlMixIn,
    EntityUnitMixIn,
    YearlyReportMixIn,
    PDFReportMixIn,
    DetailView,
):
    """Fiscal-year income statement for an authorized entity."""

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
            context['unit_model'] = get_object_or_404(
                entity_unit_qs, slug__exact=unit_slug, entity__slug__exact=self.kwargs['entity_slug']
            )
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


# -----------------
# RETRIEVE — Cash Flow Statement
# -----------------
class BaseCashFlowStatementRedirectView(DjangoLedgerSecurityMixIn, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse('django_ledger:entity-cf-year', kwargs={'entity_slug': self.kwargs['entity_slug'], 'year': year})


class FiscalYearCashFlowStatementView(
    EntityModelModelBaseView,
    BaseDateNavigationUrlMixIn,
    EntityUnitMixIn,
    YearlyReportMixIn,
    PDFReportMixIn,
    DetailView,
):
    """Fiscal-year cash flow statement for an authorized entity."""

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
            context['unit_model'] = get_object_or_404(
                entity_unit_qs, slug__exact=unit_slug, entity__slug__exact=self.kwargs['entity_slug']
            )
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
