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
from django.views.generic import ListView, DetailView, UpdateView, CreateView, RedirectView
from django.views.generic.detail import SingleObjectMixin

from django_ledger.forms.journal_entry import JournalEntryModelUpdateForm, JournalEntryModelCreateForm
from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


# JE Views ---
class JournalEntryListView(DjangoLedgerSecurityMixIn, ListView):
    context_object_name = 'journal_entries'
    template_name = 'django_ledger/journal_entry/je_list.html'
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
        ).select_related('entity_unit').order_by(sort)


class JournalEntryDetailView(DjangoLedgerSecurityMixIn, DetailView):
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

    def get_queryset(self):
        return JournalEntryModel.on_coa.for_ledger(
            entity_slug=self.kwargs['entity_slug'],
            ledger_pk=self.kwargs['ledger_pk'],
            user_model=self.request.user
        ).select_related('entity_unit')


class JournalEntryUpdateView(DjangoLedgerSecurityMixIn, UpdateView):
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
        return JournalEntryModel.on_coa.for_ledger(
            entity_slug=self.kwargs['entity_slug'],
            ledger_pk=self.kwargs['ledger_pk'],
            user_model=self.request.user
        ).prefetch_related('transactionmodel_set', 'transactionmodel_set__account')


class JournalEntryCreateView(DjangoLedgerSecurityMixIn, CreateView):
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
            'timestamp': localdate(),
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
