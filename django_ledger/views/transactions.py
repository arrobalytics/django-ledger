"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from django_ledger.forms.transactions import TransactionModelFormSet
from django_ledger.models import JournalEntryModel
from django_ledger.models.transactions import TransactionModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class TXSJournalEntryView(DjangoLedgerSecurityMixIn, TemplateView):
    template_name = 'django_ledger/transaction/txs.html'
    PAGE_TITLE = _('Edit Transactions')
    extra_context = {
        'header_title': PAGE_TITLE,
        'page_title': PAGE_TITLE
    }

    def get_context_data(self, txs_formset=None, **kwargs):
        context = super(TXSJournalEntryView, self).get_context_data(**kwargs)
        if not txs_formset:
            context['txs_formset'] = TransactionModelFormSet(
                user_model=self.request.user,
                je_pk=self.kwargs['je_pk'],
                ledger_pk=self.kwargs['ledger_pk'],
                entity_slug=self.kwargs['entity_slug'],
                # queryset=self.get_queryset()
            )
        else:
            context['txs_formset'] = txs_formset
        return context

    def post(self, request, **kwargs):


        je_qs = JournalEntryModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )
        je_model: JournalEntryModel = get_object_or_404(je_qs, uuid=self.kwargs['je_pk'])

        txs_formset = TransactionModelFormSet(request.POST,
                                              user_model=self.request.user,
                                              ledger_pk=kwargs['ledger_pk'],
                                              entity_slug=kwargs['entity_slug'],
                                              je_pk=kwargs['je_pk'])

        if je_model.locked:
            messages.add_message(self.request,
                                 message=_('Cannot update a Locked Journal Entry.'),
                                 level=messages.ERROR,
                                 extra_tags='is-danger')
            return self.render_to_response(
                context=self.get_context_data(txs_formset=txs_formset)
            )

        context = self.get_context_data()
        if txs_formset.is_valid():
            txs_list = txs_formset.save(commit=False)

            for txs in txs_list:
                if not txs.journal_entry_id:
                    txs.journal_entry_id = je_model.uuid

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
