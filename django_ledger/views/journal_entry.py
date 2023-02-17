"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.journal_entry import JournalEntryModelUpdateForm, JournalEntryModelCreateForm
from django_ledger.forms.transactions import get_transactionmodel_formset_class
from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class JournalEntryModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if not self.queryset:
            self.queryset = JournalEntryModel.objects.for_ledger(
                ledger_pk=self.kwargs['ledger_pk'],
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).select_related('entity_unit', 'ledger', 'ledger__entity')
        return super().get_queryset()


# JE Views ---
class JournalEntryListView(DjangoLedgerSecurityMixIn, JournalEntryModelModelViewQuerySetMixIn, ListView):
    context_object_name = 'journal_entries'
    template_name = 'django_ledger/journal_entry/je_list.html'
    PAGE_TITLE = _('Journal Entries')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    http_method_names = ['get']


class JournalEntryDetailView(DjangoLedgerSecurityMixIn, JournalEntryModelModelViewQuerySetMixIn, DetailView):
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


class JournalEntryModelTXSDetailView(DjangoLedgerSecurityMixIn, JournalEntryModelModelViewQuerySetMixIn, DetailView):
    template_name = 'django_ledger/journal_entry/je_detail_txs.html'
    PAGE_TITLE = _('Edit Transactions')
    pk_url_kwarg = 'je_pk'
    extra_context = {
        'header_title': PAGE_TITLE,
        'page_title': PAGE_TITLE
    }

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related('transactionmodel_set', 'transactionmodel_set__account')

    def get_context_data(self, txs_formset=None, **kwargs):
        context = super(JournalEntryModelTXSDetailView, self).get_context_data(**kwargs)
        je_model: JournalEntryModel = self.object
        if je_model.locked:
            messages.add_message(self.request,
                                 message=_('Locked Journal Entry. Must unlock to Edit.'),
                                 level=messages.WARNING,
                                 extra_tags='is-warning')
        if not txs_formset:
            TransactionModelFormSet = get_transactionmodel_formset_class(journal_entry_model=je_model)
            context['txs_formset'] = TransactionModelFormSet(
                user_model=self.request.user,
                je_model=je_model,
                ledger_pk=self.kwargs['ledger_pk'],
                entity_slug=self.kwargs['entity_slug'],
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
                                              user_model=self.request.user,
                                              ledger_pk=kwargs['ledger_pk'],
                                              entity_slug=kwargs['entity_slug'],
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
            return self.render_to_response(context=self.get_context_data(txs_formset=txs_formset))
        return self.render_to_response(context=self.get_context_data())


class JournalEntryUpdateView(DjangoLedgerSecurityMixIn, JournalEntryModelModelViewQuerySetMixIn, UpdateView):
    context_object_name = 'journal_entry'
    template_name = 'django_ledger/journal_entry/je_update.html'
    pk_url_kwarg = 'je_pk'
    PAGE_TITLE = _('Update Journal Entry')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_form(self, form_class=None):
        return JournalEntryModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            ledger_pk=self.kwargs['ledger_pk'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:je-list', kwargs={
            'entity_slug': self.kwargs['entity_slug'],
            'ledger_pk': self.kwargs['ledger_pk']
        })

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related('transactionmodel_set', 'transactionmodel_set__account')


class JournalEntryCreateView(DjangoLedgerSecurityMixIn, JournalEntryModelModelViewQuerySetMixIn, CreateView):
    template_name = 'django_ledger/journal_entry/je_create.html'
    PAGE_TITLE = _('Create Journal Entry')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_form(self, form_class=None):
        return JournalEntryModelCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            ledger_pk=self.kwargs['ledger_pk'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        ledger_model = LedgerModel.objects.for_entity(
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug'],
        ).get(uuid__exact=self.kwargs['ledger_pk'])
        je_model: JournalEntryModel = form.save(commit=False)
        je_model.ledger = ledger_model
        return super().form_valid(form)

    def get_initial(self):
        return {
            'timestamp': localtime(),
            'ledger': LedgerModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).get(uuid__exact=self.kwargs['ledger_pk'])
        }

    def get_success_url(self):
        return reverse('django_ledger:je-list',
                       kwargs={
                           'entity_slug': self.kwargs.get('entity_slug'),
                           'ledger_pk': self.kwargs.get('ledger_pk')
                       })


# ACTION VIEWS...
class BaseJournalEntryActionView(DjangoLedgerSecurityMixIn, RedirectView, SingleObjectMixin):
    http_method_names = ['get']
    pk_url_kwarg = 'je_pk'
    action_name = None
    commit = True

    def get_queryset(self):
        return JournalEntryModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_redirect_url(self, *args, **kwargs):
        return reverse('django_ledger:je-list',
                       kwargs={
                           'entity_slug': kwargs['entity_slug'],
                           'ledger_pk': kwargs['ledger_pk']
                       })

    def get(self, request, *args, **kwargs):
        kwargs['user_model'] = self.request.user
        if not self.action_name:
            raise ImproperlyConfigured('View attribute action_name is required.')
        response = super(BaseJournalEntryActionView, self).get(request, *args, **kwargs)
        je_model: BaseJournalEntryActionView = self.get_object()

        try:
            getattr(je_model, self.action_name)(commit=self.commit,
                                                verify=True,
                                                raise_exception=True, **kwargs)
        except ValidationError as e:
            messages.add_message(request,
                                 message=e.message,
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
        return response


class JournalEntryActionMarkAsPostedView(BaseJournalEntryActionView):
    action_name = 'mark_as_posted'


class JournalEntryActionMarkAsUnPostedView(BaseJournalEntryActionView):
    action_name = 'mark_as_unposted'


class JournalEntryActionMarkAsLockedView(BaseJournalEntryActionView):
    action_name = 'mark_as_locked'


class JournalEntryActionMarkAsUnLockedView(BaseJournalEntryActionView):
    action_name = 'mark_as_unlocked'
