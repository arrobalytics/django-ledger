"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""
from typing import Optional

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    ArchiveIndexView, YearArchiveView,
    MonthArchiveView, DetailView,
    CreateView,
    DeleteView, UpdateView
)
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.closing_entry import ClosingEntryCreateForm, ClosingEntryUpdateForm
from django_ledger.io.io_core import get_localdate
from django_ledger.models import EstimateModel, ClosingEntryModelQuerySet
from django_ledger.models.closing_entry import ClosingEntryModel
from django_ledger.models.entity import EntityModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, DjangoLedgerActionViewMixIn


class ClosingEntryModelBaseView(DjangoLedgerSecurityMixIn):
    """
    Shared closing-entry queryset scoped to the authorized business.
    """
    queryset: Optional[ClosingEntryModelQuerySet] = None

    def get_queryset(self):
        if self.queryset is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            closing_entry_model_qs = entity_model.closingentrymodel_set.all().select_related(
                'entity_model',
                'ledger_model'
            ).order_by('-closing_date')
            self.queryset = closing_entry_model_qs
        return self.queryset


class ClosingEntryModelListView(ClosingEntryModelBaseView, ArchiveIndexView):
    """
    Lists year-end and period closing entries so you can see which periods
    have been closed.
    """
    template_name = 'django_ledger/closing_entry/closing_entry_list.html'
    date_field = 'closing_date'
    allow_future = False
    context_object_name = 'closing_entry_list'
    PAGE_TITLE = _('Closing Entry List')
    paginate_by = 10
    paginate_orphans = 2
    allow_empty = True
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'file-icons:finaldraft'
    }


class ClosingEntryModelYearListView(ClosingEntryModelListView, YearArchiveView):
    """
    Lists closing entries for a selected year.
    """
    paginate_by = 10
    make_object_list = True


class ClosingEntryModelMonthListView(ClosingEntryModelListView, MonthArchiveView):
    """
    Lists closing entries for a selected month.
    """
    paginate_by = 10
    month_format = '%m'
    date_list_period = 'year'


class ClosingEntryModelCreateView(ClosingEntryModelBaseView, CreateView):
    """
    Closes the books as of a selected date and creates the closing entry.
    """
    template_name = 'django_ledger/closing_entry/closing_entry_create.html'
    PAGE_TITLE = _('Create Closing Entry')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'file-icons:finaldraft'
    }
    form_class = ClosingEntryCreateForm

    def get_initial(self):
        return {
            'closing_date': get_localdate(),
            'entity_model': self.AUTHORIZED_ENTITY_MODEL
        }

    def get_form_kwargs(self, **kwargs):
        return super().get_form_kwargs(**kwargs) | {
            'entity_model': self.AUTHORIZED_ENTITY_MODEL
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        entity_model: EntityModel = self.get_authorized_entity_instance()
        ctx['header_subtitle'] = entity_model.name
        return ctx

    def form_valid(self, form):
        closing_date = form.cleaned_data['closing_date']
        entity_model: EntityModel = self.get_authorized_entity_instance()
        ce_model, _ = entity_model.close_entity_books(
            closing_date=closing_date,
            force_update=True,
            post_closing_entry=False
        )
        self.ce_model: EstimateModel = ce_model
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            viewname='django_ledger:closing-entry-detail',
            kwargs={
                'entity_slug': self.kwargs['entity_slug'],
                'closing_entry_pk': self.ce_model.uuid
            }
        )


class ClosingEntryModelDetailView(ClosingEntryModelBaseView, DetailView):
    """
    Shows a closing entry and the account balances locked for that date.
    """
    template_name = 'django_ledger/closing_entry/closing_entry_detail.html'
    pk_url_kwarg = 'closing_entry_pk'
    context_object_name = 'closing_entry_model'
    extra_context = {
        'header_title': 'Closing Entry Detail',
        'header_subtitle_icon': 'file-icons:finaldraft'
    }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        closing_entry_model = ctx['object']
        ctx['page_title'] = f'Closing Entry {closing_entry_model.closing_date}'
        closing_entry_txs_qs = closing_entry_model.closingentrytransactionmodel_set.all()
        ctx['closing_entry_txs_qs'] = closing_entry_txs_qs.select_related(
            'account_model', 'account_model__coa_model', 'unit_model')
        return ctx


class ClosingEntryModelUpdateView(ClosingEntryModelBaseView, UpdateView):
    """
    Updates notes or settings on an existing closing entry.
    """
    template_name = 'django_ledger/closing_entry/closing_entry_update.html'
    pk_url_kwarg = 'closing_entry_pk'
    form_class = ClosingEntryUpdateForm
    context_object_name = 'closing_entry_model'
    extra_context = {
        'header_title': 'Closing Entry Detail',
        'header_subtitle_icon': 'file-icons:finaldraft'
    }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        closing_entry_model = ctx['object']
        ctx['page_title'] = f'Closing Entry {closing_entry_model.closing_date} Update'
        closing_entry_txs_qs = closing_entry_model.closingentrytransactionmodel_set.all()
        ctx['closing_entry_txs_qs'] = closing_entry_txs_qs.select_related(
            'account_model', 'account_model__coa_model', 'unit_model')
        return ctx

    def get_success_url(self):
        return reverse(
            viewname='django_ledger:closing-entry-detail',
            kwargs={
                'entity_slug': self.kwargs['entity_slug'],
                'closing_entry_pk': self.object.uuid
            }
        )


class ClosingEntryDeleteView(ClosingEntryModelBaseView, DeleteView):
    """
    Deletes a closing entry when a period needs to be reopened.
    """
    template_name = 'django_ledger/closing_entry/closing_entry_delete.html'
    pk_url_kwarg = 'closing_entry_pk'
    context_object_name = 'closing_entry'
    extra_context = {
        'header_title': _('Delete Closing Entry'),
        'header_subtitle_icon': 'file-icons:finaldraft'
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        closing_entry_model: ClosingEntryModel = self.object
        entity_model: EntityModel = self.get_authorized_entity_instance()
        context['page_title'] = 'Delete Closing Entry {}'.format(closing_entry_model.closing_date)
        context['header_subtitle'] = entity_model.name
        return context

    def get_success_url(self):
        return reverse(viewname='django_ledger:closing-entry-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


class ClosingEntryModelActionView(
    ClosingEntryModelBaseView,
    DjangoLedgerActionViewMixIn,
    SingleObjectMixin,
    View,
):
    """
    Applies closing-entry actions such as posting or unposting the entry.
    """
    pk_url_kwarg = 'closing_entry_pk'
    action_name = None
    commit = True

    def get_redirect_url(self) -> str:
        return reverse(
            'django_ledger:closing-entry-detail',
            kwargs={
                'entity_slug': self.kwargs['entity_slug'],
                'closing_entry_pk': self.kwargs['closing_entry_pk'],
            },
        )
