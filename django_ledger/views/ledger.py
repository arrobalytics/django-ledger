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
    MonthlyReportMixIn, DjangoLedgerSecurityMixIn, DateReportMixIn, SessionConfigurationMixIn, BaseDateNavigationUrlMixIn,
    EntityUnitMixIn)


class LedgerModelListView(DjangoLedgerSecurityMixIn, ListView):
    context_object_name = 'ledgers'
    template_name = 'django_ledger/ledger_list.html'
    PAGE_TITLE = _('Entity Ledgers')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_queryset(self):
        sort = self.request.GET.get('sort')
        if not sort:
            sort = '-updated'
        entity_slug = self.kwargs.get('entity_slug')
        return LedgerModel.objects.for_entity(
            entity_slug=entity_slug,
            user_model=self.request.user
        ).order_by(sort)


class LedgerModelCreateView(DjangoLedgerSecurityMixIn, CreateView):
    template_name = 'django_ledger/ledger_create.html'
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


class LedgerModelUpdateView(DjangoLedgerSecurityMixIn, UpdateView):
    template_name = 'django_ledger/ledger_update.html'
    context_object_name = 'ledger'
    slug_url_kwarg = 'ledger_pk'
    slug_field = 'uuid'

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

    def get_queryset(self):
        entity_slug = self.kwargs['entity_slug']
        return LedgerModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=entity_slug
        )

    def get_success_url(self):
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


# Ledger Balance Sheet Views...
class BaseLedgerBalanceSheetView(DjangoLedgerSecurityMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        year = localdate().year
        return reverse('django_ledger:ledger-bs-year', kwargs={
            'entity_slug': self.kwargs['entity_slug'],
            'ledger_pk': self.kwargs['ledger_pk'],
            'year': year
        })


class FiscalYearLedgerBalanceSheetView(DjangoLedgerSecurityMixIn,
                                       SessionConfigurationMixIn,
                                       BaseDateNavigationUrlMixIn,
                                       EntityUnitMixIn,
                                       YearlyReportMixIn,
                                       DetailView):
    context_object_name = 'ledger'
    template_name = 'django_ledger/balance_sheet.html'
    slug_url_kwarg = 'ledger_pk'
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Ledger Balance Sheet: ') + self.object.name
        context['header_title'] = context['page_title']
        return context

    def get_queryset(self):
        entity_slug = self.kwargs['entity_slug']
        return LedgerModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=entity_slug)


class QuarterlyLedgerBalanceSheetView(QuarterlyReportMixIn, FiscalYearLedgerBalanceSheetView):
    """
    Quarter Balance Sheet View.
    """


class MonthlyLedgerBalanceSheetView(MonthlyReportMixIn, FiscalYearLedgerBalanceSheetView):
    """
    Monthly Balance Sheet View.
    """


class DateLedgerBalanceSheetView(DateReportMixIn, FiscalYearLedgerBalanceSheetView):
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
                                          SessionConfigurationMixIn,
                                          BaseDateNavigationUrlMixIn,
                                          EntityUnitMixIn,
                                          YearlyReportMixIn,
                                          DetailView):
    context_object_name = 'ledger'
    template_name = 'django_ledger/income_statement.html'
    slug_url_kwarg = 'ledger_pk'
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Ledger Income Statement: ') + self.object.name
        context['header_title'] = context['page_title']
        return context

    def get_queryset(self):
        entity_slug = self.kwargs['entity_slug']
        return LedgerModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=entity_slug)


class QuarterlyLedgerIncomeStatementView(QuarterlyReportMixIn, FiscalYearLedgerIncomeStatementView):
    """
    Quarterly Income Statement Quarter Report.
    """


class MonthlyLedgerIncomeStatementView(MonthlyReportMixIn, FiscalYearLedgerIncomeStatementView):
    """
    Monthly Income Statement Monthly Report.
    """


class DateLedgerIncomeStatementView(DateReportMixIn, FiscalYearLedgerIncomeStatementView):
    """
    Date Income Statement Monthly Report.
    """
