from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView, DetailView, UpdateView, CreateView

from django_ledger.forms import JournalEntryModelUpdateForm, JournalEntryModelCreateForm
from django_ledger.models import LedgerModel, JournalEntryModel


# JE Views ---
class JournalEntryListView(ListView):
    context_object_name = 'jes'
    template_name = 'django_ledger/je_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('journal entries')
        context['header_title'] = _('journal entries')
        return context

    def get_queryset(self):
        sort = self.request.GET.get('sort')
        if not sort:
            sort = '-updated'
        entity_slug = self.kwargs.get('entity_slug')
        ledger_pk = self.kwargs.get('ledger_pk')
        return JournalEntryModel.on_coa.for_user(
            user_model=self.request.user).filter(
            Q(ledger__entity__slug=entity_slug) &
            Q(ledger__slug__iexact=ledger_pk)
        ).order_by(sort)


class JournalEntryDetailView(DetailView):
    pk_url_kwarg = 'je_pk'
    context_object_name = 'journal_entry'
    template_name = 'django_ledger/je_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('journal entry detail')
        context['header_title'] = _('journal entry detail')
        return context

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return JournalEntryModel.on_coa.for_user(
            user_model=self.request.user).filter(
            ledger__entity__slug__iexact=entity_slug).prefetch_related('txs', 'txs__account')


class JournalEntryUpdateView(UpdateView):
    pk_url_kwarg = 'je_pk'
    context_object_name = 'journal_entry'
    template_name = 'django_ledger/je_update.html'

    def get_form(self, form_class=None):
        return JournalEntryModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            ledger_pk=self.kwargs['ledger_pk'],
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:je-list', kwargs={
            'entity_slug': self.kwargs['entity_slug'],
            'ledger_pk': self.kwargs['ledger_pk']
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('update journal entry')
        context['header_title'] = _('update journal entry')
        return context

    def get_queryset(self):
        entity_slug = self.kwargs.get('entity_slug')
        return JournalEntryModel.on_coa.for_user(
            user_model=self.request.user).filter(
            ledger__entity__slug__iexact=entity_slug).prefetch_related('txs', 'txs__account')


class JournalEntryCreateView(CreateView):
    template_name = 'django_ledger/je_create.html'

    def get_form(self, form_class=None):
        return JournalEntryModelCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            ledger_pk=self.kwargs['ledger_pk'],
            **self.get_form_kwargs()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('create journal entry')
        context['header_title'] = _('create journal entry')
        return context

    def form_valid(self, form):
        ledger_model = LedgerModel.objects.for_user(
            user_model=self.request.user
        ).get(id=self.kwargs['ledger_pk'])
        form.instance.ledger = ledger_model
        self.object = form.save()
        return super().form_valid(form)

    def get_initial(self):
        ledger_pk = self.kwargs.get('ledger_pk')
        return {
            'ledger': LedgerModel.objects.get(pk=ledger_pk)
        }

    def get_success_url(self):
        return reverse('django_ledger:je-list',
                       kwargs={
                           'entity_slug': self.kwargs.get('entity_slug'),
                           'ledger_pk': self.kwargs.get('ledger_pk')
                       })