"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""


from typing import Optional

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DetailView, RedirectView

from django_ledger.forms.unit import EntityUnitModelCreateForm, EntityUnitModelUpdateForm
from django_ledger.io.io_core import get_localdate
from django_ledger.models import EntityUnitModel, EntityModel
from django_ledger.models.unit import EntityUnitModelQuerySet
from django_ledger.views.financial_statement import FiscalYearIncomeStatementView
from django_ledger.views.mixins import (DjangoLedgerSecurityMixIn, QuarterlyReportMixIn, MonthlyReportMixIn,
                                        DateReportMixIn, BaseDateNavigationUrlMixIn, EntityUnitMixIn, YearlyReportMixIn,
                                        PDFReportMixIn)

class EntityUnitModelModelBaseView(DjangoLedgerSecurityMixIn):
    """
    Shared business-unit queryset scoped to the authorized business.
    """
    queryset: Optional[EntityUnitModelQuerySet] = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = EntityUnitModel.objects.for_entity(
                entity_model=self.get_authorized_entity_instance()
            ).select_related('entity')
        return super().get_queryset()


class EntityUnitModelListView(EntityUnitModelModelBaseView, ListView):
    """
    Lists departments or locations used to segment the books.
    """
    template_name = 'django_ledger/unit/unit_list.html'
    PAGE_TITLE = _('Entity Unit List')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        # 'header_subtitle_icon': 'dashicons:businesswoman'
    }
    context_object_name = 'unit_list'


class EntityUnitModelCreateView(EntityUnitModelModelBaseView, CreateView):
    """
    Creates a business unit such as a store, department, or project.
    """
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
        entity_model: EntityModel = self.get_authorized_entity_instance()
        entity_unit_model.entity = entity_model
        EntityUnitModel.add_root(instance=entity_unit_model)
        return HttpResponseRedirect(self.get_success_url())


class EntityUnitModelDetailView(EntityUnitModelModelBaseView, DetailView):
    """
    Shows details for a business unit.
    """
    template_name = 'django_ledger/unit/unit_detail.html'
    PAGE_TITLE = _('Entity Unit Detail')
    slug_url_kwarg = 'unit_slug'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        # 'header_subtitle_icon': 'dashicons:businesswoman'
    }
    context_object_name = 'unit'


class EntityUnitUpdateView(EntityUnitModelModelBaseView, UpdateView):
    """
    Updates a business unit name and settings.
    """
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


class BaseEntityUnitModelBalanceSheetView(EntityUnitModelModelBaseView, RedirectView):

    """

    Opens the current-year balance sheet for a business unit.

    """

    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse('django_ledger:unit-bs-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'unit_slug': self.kwargs['unit_slug'],
                           'year': year
                       })


class FiscalYearEntityUnitModelBalanceSheetView(EntityUnitModelModelBaseView,
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
    Balance sheet for a business unit over a fiscal quarter.
    """


class MonthlyEntityUnitModelBalanceSheetView(FiscalYearEntityUnitModelBalanceSheetView, MonthlyReportMixIn):
    """
    Balance sheet for a business unit over a month.
    """


class DateEntityUnitModelBalanceSheetView(MonthlyEntityUnitModelBalanceSheetView, DateReportMixIn):
    """
    Balance sheet for a business unit as of a specific date.
    """


class BaseEntityUnitModelIncomeStatementView(EntityUnitModelModelBaseView, RedirectView):

    """

    Opens the current-year income statement for a business unit.

    """

    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse('django_ledger:unit-ic-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'unit_slug': self.kwargs['unit_slug'],
                           'year': year
                       })


class FiscalYearEntityUnitModelIncomeStatementView(EntityUnitModelModelBaseView,
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
    Income statement for a business unit over a fiscal quarter.
    """


class MonthlyIncomeStatementView(FiscalYearIncomeStatementView, MonthlyReportMixIn):
    """
    Income statement for a business unit over a month.
    """


class DateIncomeStatementView(FiscalYearIncomeStatementView, DateReportMixIn):
    """
    Income statement for a business unit as of a specific date.
    """


class BaseEntityUnitModelCashFlowStatementView(EntityUnitModelModelBaseView, RedirectView):

    """

    Opens the current-year cash flow statement for a business unit.

    """

    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse('django_ledger:unit-cf-year',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug'],
                           'unit_slug': self.kwargs['unit_slug'],
                           'year': year
                       })


class FiscalYearEntityUnitModelCashFlowStatementView(EntityUnitModelModelBaseView,
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
