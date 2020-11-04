from django.forms import ModelForm, modelformset_factory, BaseModelFormSet, TextInput, Select, HiddenInput

from django_ledger.io import validate_tx_data
from django_ledger.models.accounts import AccountModel
from django_ledger.models.journalentry import JournalEntryModel
from django_ledger.models.transactions import TransactionModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class TransactionModelForm(ModelForm):
    class Meta:
        model = TransactionModel
        fields = [
            'journal_entry',
            'account',
            'tx_type',
            'amount',
            'description'
        ]
        widgets = {
            'journal_entry': HiddenInput(attrs={
                'readonly': True
            }),
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


class BaseTransactionModelFormSet(BaseModelFormSet):

    def __init__(self, *args, entity_slug, ledger_pk, user_model, je_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.JE_PK = je_pk
        self.LEDGER_PK = ledger_pk
        self.ENTITY_SLUG = entity_slug

        account_qs = AccountModel.on_coa.for_entity_available(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG
        )

        je_qs = JournalEntryModel.on_coa.for_ledger(
            ledger_pk=self.LEDGER_PK,
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        if je_pk:
            je_qs = je_qs.filter(uuid__exact=self.JE_PK)

        for form in self.forms:
            form.fields['account'].queryset = account_qs
            form.fields['journal_entry'].queryset = je_qs

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
        validate_tx_data(txs_balances)


TransactionModelFormSet = modelformset_factory(
    model=TransactionModel,
    form=TransactionModelForm,
    formset=BaseTransactionModelFormSet,
    can_delete=True,
    extra=6)
