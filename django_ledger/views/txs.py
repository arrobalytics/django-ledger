from django.contrib import messages
from django.urls import reverse
from django.views.generic import TemplateView, ListView

from django_ledger.forms.transactions import TransactionModelFormSet
from django_ledger.models.transactions import TransactionModel


# TXS View ---
# todo: rename to JE Transactions
class TXSJournalEntryView(TemplateView):
    template_name = 'django_ledger/txs.html'

    def get_queryset(self):
        return TransactionModel.objects.for_journal_entry(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            je_pk=self.kwargs['je_pk'],
            ledger_slug=self.kwargs['ledger_pk']
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

        txs_formset = TransactionModelFormSet(
            user_model=self.request.user,
            entity_slug=kwargs['entity_slug'],
            queryset=self.get_queryset()
        )

        context['txs_formset'] = txs_formset
        return self.render_to_response(context)

    def post(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        txs_formset = TransactionModelFormSet(request.POST,
                                              user_model=self.request.user,
                                              entity_slug=kwargs['entity_slug']
                                              )
        if txs_formset.is_valid():
            for f in txs_formset:
                f.instance.journal_entry_id = context['je_pk']
            txs_formset.save()
            context['txs_formset'] = txs_formset
            messages.add_message(request, messages.SUCCESS, 'Successfully saved transactions.', extra_tags='is-success')
        else:
            context['txs_formset'] = txs_formset
            messages.add_message(request,
                                 messages.ERROR,
                                 'Hmmm, this doesn\'t add up!. Check your math!',
                                 extra_tags='is-danger')
        return self.render_to_response(context)


class TXSAccountView(ListView):
    template_name = 'django_ledger/txs_account.html'

    def get_queryset(self):
        # todo: prefect account details?...
        return TransactionModel.objects.for_account(
            account_pk=self.kwargs['account_pk'],
            coa_slug=self.kwargs['coa_slug'],
            user_model=self.request.user,
            entity_slug=self.kwargs['entity_slug']
        )
