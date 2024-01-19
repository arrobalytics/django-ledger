"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    DetailView, UpdateView, CreateView,
    RedirectView, DeleteView, ArchiveIndexView, YearArchiveView, MonthArchiveView
)
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.ledger import LedgerModelCreateForm, LedgerModelUpdateForm
from django_ledger.models.ledger import LedgerModel
from django_ledger.views.mixins import (
    YearlyReportMixIn, QuarterlyReportMixIn,
    MonthlyReportMixIn, DjangoLedgerSecurityMixIn, DateReportMixIn, BaseDateNavigationUrlMixIn,
    EntityUnitMixIn, PDFReportMixIn
)


class LedgerModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = LedgerModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).select_related('entity')
        return self.queryset


class LedgerModelListView(DjangoLedgerSecurityMixIn, LedgerModelModelViewQuerySetMixIn, ArchiveIndexView):
    context_object_name = 'ledger_list'
    template_name = 'django_ledger/ledger/ledger_list.html'
    PAGE_TITLE = _('Entity Ledgers')
    paginate_by = 30
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
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
    make_object_list = True


class LedgerModelMonthListView(MonthArchiveView, LedgerModelListView):
    make_object_list = True


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
        instance = form.save(commit=False)
        instance.entity = self.AUTHORIZED_ENTITY_MODEL
        self.object = form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


class LedgerModelDetailView(DjangoLedgerSecurityMixIn, LedgerModelModelViewQuerySetMixIn, RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:je-list',
                       kwargs={
                           'ledger_pk': self.kwargs['ledger_pk'],
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


class LedgerModelDeleteView(DjangoLedgerSecurityMixIn, LedgerModelModelViewQuerySetMixIn, DeleteView):
    template_name = 'django_ledger/ledger/ledger_delete.html'
    pk_url_kwarg = 'ledger_pk'
    context_object_name = 'ledger_model'

    def get_success_url(self):
        return reverse(viewname='django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


# ACTIONS....

class LedgerModelModelActionView(DjangoLedgerSecurityMixIn,
                                 RedirectView,
                                 LedgerModelModelViewQuerySetMixIn,
                                 SingleObjectMixin):
    http_method_names = ['get']
    pk_url_kwarg = 'ledger_pk'
    action_name = None
    commit = True

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': kwargs['entity_slug']
                       })

    def get(self, request, *args, **kwargs):
        kwargs['user_model'] = self.request.user
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(LedgerModelModelActionView, self).get(request, *args, **kwargs)
        ledger_model: LedgerModel = self.get_object()

        try:
            getattr(ledger_model, self.action_name)(commit=self.commit, **kwargs)
        except ValidationError as e:
            messages.add_message(request,
                                 message=e.message,
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
        return response


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
