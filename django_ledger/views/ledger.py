"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Ledger views grouped by CRUD + Actions + Statements.

  * CREATE   — LedgerModelCreateView
  * RETRIEVE — List / Year / Month; detail redirects to JE list
  * UPDATE   — LedgerModelUpdateView
  * DELETE   — LedgerModelDeleteView
  * ACTIONS  — post / lock / hide via LedgerModelModelActionView
  * REPORTS — Balance Sheet / Income Statement / Cash Flow
"""

from typing import Optional

from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
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

from django_ledger.forms.ledger import LedgerModelCreateForm, LedgerModelUpdateForm
from django_ledger.io.io_core import get_localdate
from django_ledger.models import EntityModel
from django_ledger.models.ledger import LedgerModel, LedgerModelQuerySet
from django_ledger.views.mixins import (
    BaseDateNavigationUrlMixIn,
    DateReportMixIn,
    DjangoLedgerSecurityMixIn,
    DjangoLedgerActionView,
    EntityUnitMixIn,
    MonthlyReportMixIn,
    PDFReportMixIn,
    QuarterlyReportMixIn,
    YearlyReportMixIn,
)


class LedgerModelModelBaseView(DjangoLedgerSecurityMixIn):
    """Entity-scoped ledger queryset shared by all ledger CRUD/action/report views."""

    queryset: Optional[LedgerModelQuerySet] = None

    def get_queryset(self) -> LedgerModelQuerySet:
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            qs: LedgerModelQuerySet = entity_model.get_ledgers()
            self.queryset = qs
        return self.queryset


# -----------------
# RETRIEVE (List)
# -----------------
class LedgerModelListView(LedgerModelModelBaseView, ArchiveIndexView):
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
    make_object_list = True
    year_format = '%Y'
    paginate_by = 30


class LedgerModelMonthListView(MonthArchiveView, LedgerModelListView):
    make_object_list = True
    year_format = '%Y'
    month_format = '%m'
    paginate_by = 30


# -----------------
# CREATE
# -----------------
class LedgerModelCreateView(LedgerModelModelBaseView, CreateView):
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


# -----------------
# RETRIEVE (Detail → JE list)
# -----------------
class LedgerModelDetailView(LedgerModelModelBaseView, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        return reverse(
            'django_ledger:je-list',
            kwargs={'ledger_pk': self.kwargs['ledger_pk'], 'entity_slug': self.kwargs['entity_slug']},
        )


# -----------------
# UPDATE
# -----------------
class LedgerModelUpdateView(LedgerModelModelBaseView, UpdateView):
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


# -----------------
# DELETE
# -----------------
class LedgerModelDeleteView(LedgerModelModelBaseView, DeleteView):
    template_name = 'django_ledger/ledger/ledger_delete.html'
    pk_url_kwarg = 'ledger_pk'
    context_object_name = 'ledger_model'

    def get_success_url(self):
        return reverse(viewname='django_ledger:ledger-list', kwargs={'entity_slug': self.kwargs['entity_slug']})


# ACTIONS....


# -----------------
# ACTIONS (post / lock / hide)
# -----------------
class LedgerModelModelActionView(LedgerModelModelBaseView, DjangoLedgerActionView):
    """
    Shared ledger action endpoint.

    Concrete subclasses set ``action_name`` (post, unpost, lock, unlock, hide,
    unhide, or bulk journal-entry helpers). Uses ``action_before_redirect``
    because the redirect URL depends on ``self.object``. Honors a safe
    ``next`` target; otherwise goes to the ledger's journal-entry list.
    Requires POST by default.
    """

    pk_url_kwarg = 'ledger_pk'
    action_before_redirect = True
    # user_model is passed via get_action_kwargs; do not also inject into URL kwargs.
    pass_user_model_to_kwargs = False

    def get_redirect_url(self, *args, **kwargs):
        next_url = self.get_safe_next_url()
        if next_url:
            return next_url
        ledger_model: LedgerModel = self.object
        return ledger_model.get_journal_entry_list_url()

    def get_action_kwargs(self, **kwargs):
        # Preserve prior call signature: commit + user_model + URL kwargs.
        action_kwargs = dict(kwargs)
        action_kwargs['commit'] = self.commit
        action_kwargs['user_model'] = self.request.user
        return action_kwargs


class LedgerModelActionPostView(LedgerModelModelActionView):
    """Posts the ledger so its journal entries become part of financial reports."""

    action_name = 'post'


class LedgerModelActionPostJournalEntriesView(LedgerModelModelActionView):
    """Bulk-posts all eligible journal entries belonging to the ledger."""

    action_name = 'post_journal_entries'


class LedgerModelActionUnpostView(LedgerModelModelActionView):
    """Unposts the ledger, removing it from posted financial activity."""

    action_name = 'unpost'


class LedgerModelActionLockView(LedgerModelModelActionView):
    """Locks the ledger to prevent further journal-entry edits."""

    action_name = 'lock'


class LedgerModelActionLockJournalEntriesView(LedgerModelModelActionView):
    """Bulk-locks all eligible journal entries belonging to the ledger."""

    action_name = 'lock_journal_entries'


class LedgerModelActionUnlockView(LedgerModelModelActionView):
    """Unlocks the ledger so journal entries can be edited again."""

    action_name = 'unlock'


class LedgerModelActionHideView(LedgerModelModelActionView):
    """Hides the ledger from default list views without deleting it."""

    action_name = 'hide'


class LedgerModelActionUnhideView(LedgerModelModelActionView):
    """Restores a hidden ledger to the default visible list."""

    action_name = 'unhide'


# -----------------
# REPORTS (Balance Sheet)
# -----------------
class BaseLedgerModelBalanceSheetView(LedgerModelModelBaseView, RedirectView):
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
class BaseLedgerIncomeStatementView(LedgerModelModelBaseView, RedirectView):
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
class BaseLedgerModelCashFlowStatementRedirectView(LedgerModelModelBaseView, RedirectView):
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
