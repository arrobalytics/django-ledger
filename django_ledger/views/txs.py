from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from django.views.generic import TemplateView

from django_ledger.forms import TransactionModelFormSet
from django_ledger.models import TransactionModel, JournalEntryModel


# TXS View ---
class TXSView(TemplateView):
    template_name = 'django_ledger/txs.html'

    def get_queryset(self):
        kwargs = self.kwargs
        return TransactionModel.objects.filter(
            Q(journal_entry_id=kwargs.get('je_pk')) &
            Q(journal_entry__ledger__entity__slug=kwargs.get('entity_slug')) &
            (
                    Q(journal_entry__ledger__entity__admin=self.request.user) |
                    Q(journal_entry__ledger__entity__managers__exact=self.request.user)
            )
        ).order_by('account__code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        txs_formset_url = reverse('django_ledger:txs',
                                  kwargs={
                                      'entity_slug': kwargs['entity_slug'],
                                      'ledger_pk': kwargs['ledger_pk'],
                                      'je_pk': kwargs['je_pk'],
                                  })
        context['txs_formset_url'] = txs_formset_url
        context['page_title'] = 'Edit Transactions'
        context['header_title'] = 'Edit Transactions'
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        txs_formset = TransactionModelFormSet(queryset=self.get_queryset())
        context['txs_formset'] = txs_formset
        return self.render_to_response(context)

    def post(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        txs_formset = TransactionModelFormSet(request.POST)
        je_model = JournalEntryModel.objects.filter(
            Q(id=context['je_pk']) &
            Q(ledger__entity__slug=context['entity_slug']) &
            (
                    Q(ledger__entity__admin__exact=self.request.user) |
                    Q(ledger__entity__managers__exact=self.request.user)
            )
        ).exists()
        if txs_formset.is_valid() and je_model:
            for f in txs_formset:
                f.instance.journal_entry_id = context['je_pk']
            txs_formset.save()
            txs_formset = TransactionModelFormSet(queryset=self.get_queryset())
            context['txs_formset'] = txs_formset
            messages.add_message(request, messages.SUCCESS, 'Successfully saved transactions.', extra_tags='is-success')
        else:
            context['txs_formset'] = txs_formset
            messages.add_message(request,
                                 messages.ERROR,
                                 'Hmmm, this doesn\'t add up!. Check your math!',
                                 extra_tags='is-danger')
        return self.render_to_response(context)
