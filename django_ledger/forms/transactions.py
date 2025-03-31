"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    - Miguel Sanda <msanda@arrobalytics.com>
    - Michael Noel <noel.michael87@gmail.com>
"""

from django.forms import BaseModelFormSet, ModelForm, Select, TextInput, ValidationError, modelformset_factory
from django.utils.translation import gettext_lazy as _

from django_ledger.io.io_core import check_tx_balance
from django_ledger.models.entity import EntityModel
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

    def __init__(self, *args, entity_model: EntityModel, je_model: JournalEntryModel, **kwargs):
        super().__init__(*args, **kwargs)
        je_model.validate_for_entity(entity_model)
        self.JE_MODEL: JournalEntryModel = je_model
        self.ENTITY_MODEL = entity_model

        account_qs = self.ENTITY_MODEL.get_coa_accounts().active().order_by('code')

        for form in self.forms:
            form.fields['account'].queryset = account_qs
            if self.JE_MODEL.is_locked():
                form.fields['account'].disabled = True
                form.fields['tx_type'].disabled = True
                form.fields['amount'].disabled = True

    def get_queryset(self):
        return self.JE_MODEL.transactionmodel_set.all()

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
        balance_ok = check_tx_balance(txs_balances, perform_correction=False)
        if not balance_ok:
            raise ValidationError(message=_('Credits and Debits do not balance.'))


def get_transactionmodel_formset_class(journal_entry_model: JournalEntryModel):
    can_delete = not journal_entry_model.is_locked()
    return modelformset_factory(
        model=TransactionModel,
        form=TransactionModelForm,
        formset=TransactionModelFormSet,
        can_delete=can_delete,
        extra=6 if can_delete else 0)
