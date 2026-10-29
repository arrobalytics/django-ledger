"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""
from typing import Any, Dict, Optional

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    YearArchiveView, MonthArchiveView, DetailView, UpdateView, CreateView,
    ArchiveIndexView, DeleteView
)
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.journal_entry import (
    JournalEntryModelUpdateForm,
    JournalEntryModelCannotEditForm,
    JournalEntryModelCreateForm
)
from django_ledger.forms.transactions import get_transactionmodel_formset_class
from django_ledger.io.io_core import get_localtime
from django_ledger.models import EntityModel, LedgerModel
from django_ledger.models.journal_entry import JournalEntryModel, JournalEntryModelQuerySet
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn, DjangoLedgerActionViewMixIn

class JournalEntryModelModelBaseView(DjangoLedgerSecurityMixIn):
    """
    Shared journal-entry queryset scoped to an authorized ledger.
    """
    queryset: Optional[JournalEntryModelQuerySet] = None
    ledger_model: Optional[LedgerModel] = None

    def get_queryset(self):
        if self.queryset is None:
            ledger_model: LedgerModel = self.get_ledger_model()
            journal_entry_queryset = ledger_model.journal_entries.select_related('entity_unit', 'ledger', 'ledger__entity').order_by('-timestamp')
            self.queryset = journal_entry_queryset
        return self.queryset

    def get_ledger_model(self) -> LedgerModel:
        if self.ledger_model is None:
            entity_model: EntityModel = self.get_authorized_entity_instance()
            self.ledger_model = entity_model.get_ledgers().get(uuid__exact=self.kwargs['ledger_pk'])
        return self.ledger_model


class JournalEntryListView(JournalEntryModelModelBaseView, ArchiveIndexView):
    """
    Lists journal entries in a ledger so you can review posted and draft entries.
    """
    context_object_name = 'journal_entry_qs'
    template_name = 'django_ledger/journal_entry/je_list.html'
    PAGE_TITLE = _('Journal Entries')
    http_method_names = ['get']
    date_field = 'timestamp'
    paginate_by = 20
    allow_empty = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entity_model: EntityModel = self.get_authorized_entity_instance()

        ledger_model = self.get_ledger_model()
        context['ledger_model'] = ledger_model
        context['page_title'] = self.PAGE_TITLE
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = f'{entity_model.name} | Ledger: {ledger_model.name}'
        context['header_subtitle_icon'] = 'bi:journal-check'

        if ledger_model.is_locked():
            messages.add_message(self.request,
                                 message=_('Locked Journal Entry. Must unlock ledger to add new Journal Entries.'),
                                 level=messages.WARNING,
                                 extra_tags='is-warning')
        return context


class JournalEntryYearListView(JournalEntryListView, YearArchiveView):
    """
    Lists journal entries for a selected year.
    """
    make_object_list = True


class JournalEntryMonthListView(JournalEntryListView, MonthArchiveView):
    """
    Lists journal entries for a selected month.
    """
    make_object_list = True
    month_format = '%m'


class JournalEntryCreateView(JournalEntryModelModelBaseView, CreateView):
    """
    Creates a new journal entry in a ledger.
    """
    template_name = 'django_ledger/journal_entry/je_create.html'
    PAGE_TITLE = _('Create Journal Entry')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    ledger_model: Optional[LedgerModel] = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ledger_model: LedgerModel = self.get_ledger_model()
        context['page_title'] = self.PAGE_TITLE
        context['header_title'] = self.PAGE_TITLE
        context['header_subtitle'] = ledger_model.name
        context['ledger_model'] = ledger_model
        return context

    def get_form(self, form_class=None):
        return JournalEntryModelCreateForm(
            entity_model=self.get_authorized_entity_instance(),
            ledger_model=self.get_ledger_model(),
            **self.get_form_kwargs()
        )

    def get_initial(self):
        return {
            'timestamp': get_localtime()
        }

    def get_success_url(self):
        ledger_model = self.get_ledger_model()
        return ledger_model.get_journal_entry_list_url()


class JournalEntryDetailView(JournalEntryModelModelBaseView, DetailView):
    """
    Shows a journal entry and its debit and credit lines.
    """
    context_object_name = 'journal_entry'
    template_name = 'django_ledger/journal_entry/je_detail.html'
    slug_url_kwarg = 'je_pk'
    slug_field = 'uuid'
    PAGE_TITLE = _('Journal Entry Detail')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'bi:journal-plus'
    }
    http_method_names = ['get']


class JournalEntryUpdateView(JournalEntryModelModelBaseView, UpdateView):
    """
    Updates a journal entry while it remains editable.
    """
    context_object_name = 'journal_entry'
    template_name = 'django_ledger/journal_entry/je_update.html'
    pk_url_kwarg = 'je_pk'
    PAGE_TITLE = _('Update Journal Entry')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_form_class(self, form_class=None):
        je_model: JournalEntryModel = self.object
        if not je_model.can_edit():
            return JournalEntryModelCannotEditForm
        return JournalEntryModelUpdateForm

    def get_success_url(self):
        je_model: JournalEntryModel = self.object
        return je_model.get_journal_entry_list_url()


class JournalEntryDeleteView(JournalEntryModelModelBaseView, DeleteView):
    """
    Deletes a journal entry when it is no longer needed.
    """
    template_name = 'django_ledger/journal_entry/je_delete.html'
    context_object_name = 'je_model'
    pk_url_kwarg = 'je_pk'

    def get_success_url(self) -> str:
        je_model: JournalEntryModel = self.object
        return je_model.get_journal_entry_list_url()


class JournalEntryModelTXSDetailView(JournalEntryModelModelBaseView, DetailView):
    """
    Edits the debit and credit transactions on a journal entry.
    """
    template_name = 'django_ledger/journal_entry/je_detail_txs.html'
    PAGE_TITLE = _('Edit Transactions')
    pk_url_kwarg = 'je_pk'
    extra_context = {
        'header_title': PAGE_TITLE,
        'page_title': PAGE_TITLE
    }
    context_object_name = 'journal_entry'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related('transactionmodel_set', 'transactionmodel_set__account')

    def get_context_data(self, txs_formset=None, **kwargs):
        context = super().get_context_data(**kwargs)
        je_model: JournalEntryModel = self.object
        if je_model.is_locked():
            messages.add_message(self.request,
                                 message=_('Locked Journal Entry. Must unlock to Edit.'),
                                 level=messages.WARNING,
                                 extra_tags='is-warning')
        if not txs_formset:
            TransactionModelFormSet = get_transactionmodel_formset_class(journal_entry_model=je_model)
            context['txs_formset'] = TransactionModelFormSet(
                je_model=je_model,
                entity_model=self.get_authorized_entity_instance(),
            )
        else:
            context['txs_formset'] = txs_formset
        return context

    def post(self, request, **kwargs):

        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        je_model: JournalEntryModel = self.get_object()
        self.object = je_model

        TransactionModelFormSet = get_transactionmodel_formset_class(journal_entry_model=je_model)
        txs_formset = TransactionModelFormSet(request.POST,
                                              entity_model=self.get_authorized_entity_instance(),
                                              je_model=je_model)

        if je_model.locked:
            messages.add_message(self.request,
                                 message=_('Cannot update a Locked Journal Entry.'),
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
            return self.render_to_response(context=self.get_context_data(txs_formset=txs_formset))

        if not je_model.posted:
            messages.add_message(self.request,
                                 message=_('Journal Entry has not been posted.'),
                                 level=messages.INFO,
                                 extra_tags='is-info')

        if txs_formset.is_valid():
            txs_list = txs_formset.save(commit=False)

            for txs in txs_list:
                if not txs.journal_entry_id:
                    txs.journal_entry_id = je_model.uuid

            txs_formset.save()
            messages.add_message(request, messages.SUCCESS, 'Successfully saved transactions.', extra_tags='is-success')
        else:
            messages.add_message(request,
                                 messages.ERROR,
                                 'Hmmm, this doesn\'t add up!. Check your math!',
                                 extra_tags='is-danger')
            self.render_to_response(context=self.get_context_data(txs_formset=txs_formset))
        return self.render_to_response(context=self.get_context_data())


class BaseJournalEntryActionView(
    JournalEntryModelModelBaseView,
    DjangoLedgerActionViewMixIn,
    SingleObjectMixin,
    View,
):
    """
    Applies journal-entry actions such as post, unpost, lock, or unlock.
    """
    pk_url_kwarg = 'je_pk'
    action_name = None
    commit = True

    def get_queryset(self):
        return JournalEntryModel.objects.for_entity(
            entity_model=self.AUTHORIZED_ENTITY_MODEL
        ).for_ledger(ledger_pk=self.kwargs['ledger_pk'])

    def get_action_kwargs(self) -> Dict[str, Any]:
        action_kwargs = super().get_action_kwargs()
        action_kwargs['verify'] = True
        action_kwargs['raise_exception'] = True
        return action_kwargs

    def get_redirect_url(self) -> str:
        return reverse(
            'django_ledger:je-list',
            kwargs={
                'entity_slug': self.kwargs['entity_slug'],
                'ledger_pk': self.kwargs['ledger_pk'],
            },
        )
