"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
Michael Noel <noel.michael87@gmail.com>
"""

from django.forms import ModelForm, modelformset_factory, BaseModelFormSet, TextInput, Select

from django_ledger.io import balance_tx_data
from django_ledger.models.accounts import AccountModel
from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.transactions import TransactionModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class TransactionModelForm(ModelForm):
    class Meta:
        model = TransactionModel
        fields = [
            'account',
            'tx_type',
            'amount',
            'description'
        ]
        widgets = {
            'account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'tx_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'amount': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'description': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
        }


class TransactionModelFormSet(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, ledger_pk, je_model=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.JE_MODEL: JournalEntryModel = je_model
        self.LEDGER_PK = ledger_pk
        self.ENTITY_SLUG = entity_slug
        self.queryset = self.JE_MODEL.transactionmodel_set.all().order_by('account__code')

        account_qs = AccountModel.objects.for_entity_available(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG
        ).order_by('code')

        for form in self.forms:
            form.fields['account'].queryset = account_qs
            if self.JE_MODEL.locked:
                form.fields['account'].disabled = True
                form.fields['tx_type'].disabled = True
                form.fields['amount'].disabled = True

    def clean(self):
        if any(self.errors):
            return
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
        txs_balances = [{
            'tx_type': tx.cleaned_data.get('tx_type'),
            'amount': tx.cleaned_data.get('amount')
        } for tx in self.forms if not self._should_delete_form(tx)]
        balance_tx_data(txs_balances)


def get_transactionmodel_formset_class(journal_entry_model: JournalEntryModel):
    can_delete = not journal_entry_model.locked
    return modelformset_factory(
        model=TransactionModel,
        form=TransactionModelForm,
        formset=TransactionModelFormSet,
        can_delete=can_delete,
        extra=6 if can_delete else 0)
