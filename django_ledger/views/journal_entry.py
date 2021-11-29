"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, CreateView

from django_ledger.forms.journal_entry import JournalEntryModelUpdateForm, JournalEntryModelCreateForm
from django_ledger.models.journalentry import JournalEntryModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.views.mixins import LoginRequiredMixIn


# JE Views ---
class JournalEntryListView(LoginRequiredMixIn, ListView):
    context_object_name = 'journal_entries'
    template_name = 'django_ledger/je_list.html'
    PAGE_TITLE = _('Journal Entries')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    http_method_names = ['get']

    def get_queryset(self):
        sort = self.request.GET.get('sort')
        if not sort:
            sort = '-updated'
        return JournalEntryModel.on_coa.for_ledger(
            ledger_pk=self.kwargs['ledger_pk'],
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).order_by(sort)


class JournalEntryDetailView(LoginRequiredMixIn, DetailView):
    context_object_name = 'journal_entry'
    template_name = 'django_ledger/je_detail.html'
    slug_url_kwarg = 'je_pk'
    slug_field = 'uuid'
    PAGE_TITLE = _('Journal Entry Detail')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'bi:journal-plus'
    }
    http_method_names = ['get']

    def get_queryset(self):
        return JournalEntryModel.on_coa.for_ledger(
            entity_slug=self.kwargs['entity_slug'],
            ledger_pk=self.kwargs['ledger_pk'],
            user_model=self.request.user
        ).prefetch_related('txs', 'txs__account')


class JournalEntryUpdateView(LoginRequiredMixIn, UpdateView):
    context_object_name = 'journal_entry'
    template_name = 'django_ledger/je_update.html'
    slug_url_kwarg = 'je_pk'
    PAGE_TITLE = _('Update Journal Entry')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }
    action_mark_as_posted: bool = False
    action_mark_as_locked: bool = False
    action_mark_as_unlocked: bool = False
    http_method_names = ['get', 'post']

    def get_slug_field(self):
        return 'uuid'

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
        return JournalEntryModel.on_coa.for_ledger(
            entity_slug=self.kwargs['entity_slug'],
            ledger_pk=self.kwargs['ledger_pk'],
            user_model=self.request.user
        ).prefetch_related('txs', 'txs__account')

    def get(self, request, *args, **kwargs):
        response = super(JournalEntryUpdateView, self).get(request, *args, **kwargs)
        je_model: JournalEntryModel = self.object

        if self.action_mark_as_posted:
            je_model.mark_as_posted()
        if self.action_mark_as_locked:
            je_model.mark_as_locked(commit=True)
        if self.action_mark_as_unlocked:
            je_model.mark_as_unlocked(commit=True)

        next_url = self.request.GET.get('next')
        if next_url:
            return HttpResponseRedirect(next_url)

        return response


class JournalEntryCreateView(LoginRequiredMixIn, CreateView):
    template_name = 'django_ledger/je_create.html'
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
        form.instance.ledger = ledger_model
        self.object = form.save()
        return super().form_valid(form)

    def get_initial(self):
        return {
            'date': localdate(),
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
