"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from django_ledger.forms.transactions import get_transactionmodel_formset_class
from django_ledger.models import JournalEntryModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class TXSJournalEntryView(DjangoLedgerSecurityMixIn, DetailView):
    template_name = 'django_ledger/transaction/txs.html'
    PAGE_TITLE = _('Edit Transactions')
    pk_url_kwarg = 'je_pk'
    extra_context = {
        'header_title': PAGE_TITLE,
        'page_title': PAGE_TITLE
    }

    def get_queryset(self):
        return JournalEntryModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_context_data(self, txs_formset=None, **kwargs):
        context = super(TXSJournalEntryView, self).get_context_data(**kwargs)
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
                # queryset=self.get_queryset()
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
