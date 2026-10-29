"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""

from typing import Optional

from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    ArchiveIndexView,
    CreateView,
    DeleteView,
    DetailView,
    MonthArchiveView,
    RedirectView,
    UpdateView,
    YearArchiveView,
)
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.ledger import LedgerModelCreateForm, LedgerModelUpdateForm
from django_ledger.io.io_core import get_localdate
from django_ledger.models import EntityModel
from django_ledger.models.ledger import LedgerModel, LedgerModelQuerySet
from django_ledger.views.mixins import (
    BaseDateNavigationUrlMixIn,
    DateReportMixIn,
    DjangoLedgerActionViewMixIn,
    DjangoLedgerSecurityMixIn,
    EntityUnitMixIn,
    MonthlyReportMixIn,
    PDFReportMixIn,
    QuarterlyReportMixIn,
    YearlyReportMixIn,
)

class LedgerModelModelBaseView(DjangoLedgerSecurityMixIn):
    """
    Shared ledger queryset scoped to the authorized business.
    """
    queryset: Optional[LedgerModelQuerySet] = None

    def get_queryset(self):
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            self.queryset = entity_model.get_ledgers()
        return self.queryset


class LedgerModelListView(LedgerModelModelBaseView, ArchiveIndexView):
    """
    Lists ledgers so you can open books used by bills, invoices, and journals.
    """
    allow_empty = True
    context_object_name = 'ledger_list'
    template_name = 'django_ledger/ledger/ledger_list.html'
    PAGE_TITLE = _('Entity Ledgers')
    paginate_by = 30
    extra_context = {'page_title': PAGE_TITLE, 'header_title': PAGE_TITLE}
    date_field = 'created'
    ordering = '-created'

    show_all = False
    show_current = False
    show_visible = False

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.select_related('billmodel', 'invoicemodel')
        qs = qs.order_by('-created')

        if self.show_all:
            return qs
        if self.show_current:
            qs = qs.current()
        if self.show_visible:
            qs = qs.visible()

        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(ledger_xid__icontains=search))

        return qs

    def get_context_data(self, *, object_list=None, **kwargs):
        ctx = super().get_context_data(object_list=object_list, **kwargs)
        ctx['page_title'] = self.PAGE_TITLE
        ctx['header_title'] = self.PAGE_TITLE
        if self.show_all:
            ctx['header_subtitle'] = 'All Ledger Models'
            ctx['header_subtitle_icon'] = 'emojione-monotone:ledger'
        if self.show_visible:
            ctx['header_subtitle'] = 'Visible Ledger Models'
            ctx['header_subtitle_icon'] = 'mingcute:user-visible-line'
        if self.show_current:
            ctx['header_subtitle'] = 'Current Ledger Models'
            ctx['header_subtitle_icon'] = 'basil:current-location-outline'
        return ctx


class LedgerModelYearListView(YearArchiveView, LedgerModelListView):
    """
    Lists ledgers created in a selected year.
    """
    make_object_list = True
    year_format = '%Y'
    paginate_by = 30


class LedgerModelMonthListView(MonthArchiveView, LedgerModelListView):
    """
    Lists ledgers created in a selected month.
    """
    make_object_list = True
    year_format = '%Y'
    month_format = '%m'
    paginate_by = 30


class LedgerModelCreateView(LedgerModelModelBaseView, CreateView):
    """
    Creates a new ledger book for the business.
    """
    template_name = 'django_ledger/ledger/ledger_create.html'
    PAGE_TITLE = _('Create Ledger')
    extra_context = {'page_title': PAGE_TITLE, 'header_title': PAGE_TITLE}

    def get_form(self, form_class=None):
        return LedgerModelCreateForm(
            entity_slug=self.kwargs['entity_slug'], user_model=self.request.user, **self.get_form_kwargs()
        )

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.entity = self.AUTHORIZED_ENTITY_MODEL
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('django_ledger:ledger-list', kwargs={'entity_slug': self.kwargs['entity_slug']})


class LedgerModelDetailView(LedgerModelModelBaseView, RedirectView):
    """
    Opens ledger detail or redirects into its journal activity.
    """
    def get_redirect_url(self, *args, **kwargs):
        return reverse(
            'django_ledger:je-list',
            kwargs={'ledger_pk': self.kwargs['ledger_pk'], 'entity_slug': self.kwargs['entity_slug']},
        )


class LedgerModelUpdateView(LedgerModelModelBaseView, UpdateView):
    """
    Updates a ledger name and settings.
    """
    context_object_name = 'ledger'
    pk_url_kwarg = 'ledger_pk'
    template_name = 'django_ledger/ledger/ledger_update.html'

    def get_form(self, form_class=None):
        return LedgerModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'], user_model=self.request.user, **self.get_form_kwargs()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Update Ledger: ') + self.object.name
        context['header_title'] = context['page_title']
        return context

    def get_success_url(self):
        return reverse('django_ledger:ledger-list', kwargs={'entity_slug': self.kwargs['entity_slug']})


class LedgerModelDeleteView(LedgerModelModelBaseView, DeleteView):
    """
    Deletes a ledger when it is no longer needed.
    """
    template_name = 'django_ledger/ledger/ledger_delete.html'
    pk_url_kwarg = 'ledger_pk'
    context_object_name = 'ledger_model'

    def get_success_url(self):
        return reverse(viewname='django_ledger:ledger-list', kwargs={'entity_slug': self.kwargs['entity_slug']})


class LedgerModelModelActionView(
    LedgerModelModelBaseView,
    DjangoLedgerActionViewMixIn,
    SingleObjectMixin,
    View,
):
    """
    Applies ledger actions such as post, lock, or unlock.
    """
    pk_url_kwarg = 'ledger_pk'
    action_name = None
    commit = True

    def get_redirect_url(self) -> str:
        ledger_model: LedgerModel = self.get_object()
        return ledger_model.get_journal_entry_list_url()


class BaseLedgerModelBalanceSheetView(LedgerModelModelBaseView, RedirectView):
    """
    Redirects to the current-year balance sheet for a ledger.
    """
    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse(
            'django_ledger:ledger-bs-year',
            kwargs={'entity_slug': self.kwargs['entity_slug'], 'ledger_pk': self.kwargs['ledger_pk'], 'year': year},
        )


class FiscalYearLedgerModelBalanceSheetView(
    LedgerModelModelBaseView, BaseDateNavigationUrlMixIn, EntityUnitMixIn, YearlyReportMixIn, PDFReportMixIn, DetailView
):
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
    Balance sheet for a ledger over a fiscal quarter.
    """


class MonthlyLedgerModelBalanceSheetView(FiscalYearLedgerModelBalanceSheetView, MonthlyReportMixIn):
    """
    Balance sheet for a ledger over a month.
    """


class DateLedgerModelBalanceSheetView(FiscalYearLedgerModelBalanceSheetView, DateReportMixIn):
    """
    Balance sheet for a ledger as of a specific date.
    """


class BaseLedgerIncomeStatementView(LedgerModelModelBaseView, RedirectView):
    """
    Redirects to the current-year income statement for a ledger.
    """
    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse(
            'django_ledger:ledger-ic-year',
            kwargs={'entity_slug': self.kwargs['entity_slug'], 'ledger_pk': self.kwargs['ledger_pk'], 'year': year},
        )


class FiscalYearLedgerIncomeStatementView(
    LedgerModelModelBaseView, BaseDateNavigationUrlMixIn, EntityUnitMixIn, YearlyReportMixIn, PDFReportMixIn, DetailView
):
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
    Income statement for a ledger over a fiscal quarter.
    """


class MonthlyLedgerIncomeStatementView(FiscalYearLedgerIncomeStatementView, MonthlyReportMixIn):
    """
    Income statement for a ledger over a month.
    """


class DateLedgerIncomeStatementView(FiscalYearLedgerIncomeStatementView, DateReportMixIn):
    """
    Income statement for a ledger as of a specific date.
    """


class BaseLedgerModelCashFlowStatementRedirectView(LedgerModelModelBaseView, RedirectView):
    """
    Redirects to the current-year cash flow statement for a ledger.
    """
    def get_redirect_url(self, *args, **kwargs):
        year = get_localdate().year
        return reverse(
            'django_ledger:ledger-cf-year',
            kwargs={'entity_slug': self.kwargs['entity_slug'], 'ledger_pk': self.kwargs['ledger_pk'], 'year': year},
        )


class FiscalYearLedgerModelCashFlowStatementView(
    LedgerModelModelBaseView, BaseDateNavigationUrlMixIn, EntityUnitMixIn, YearlyReportMixIn, PDFReportMixIn, DetailView
):
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
    Cash flow statement for a ledger over a fiscal quarter.
    """


class MonthlyLedgerModelCashFlowStatementView(FiscalYearLedgerModelCashFlowStatementView, MonthlyReportMixIn):
    """
    Cash flow statement for a ledger over a month.
    """


class DateLedgerModelCashFlowStatementView(FiscalYearLedgerModelCashFlowStatementView, DateReportMixIn):
    """
    Cash flow statement for a ledger as of a specific date.
    """
