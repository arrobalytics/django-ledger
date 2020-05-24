from django.forms import ModelForm, modelformset_factory, BaseModelFormSet, TextInput, Select

from django_ledger.io import validate_tx_data
from django_ledger.models import AccountModel, TransactionModel

DJETLER_FORM_INPUT_CLASS = 'input'


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
                'class': DJETLER_FORM_INPUT_CLASS,
            }),
            'tx_type': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'amount': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'description': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
        }


class BaseTransactionModelFormSet(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.ENTITY_SLUG = entity_slug
        for form in self.forms:
            form.fields['account'].queryset = AccountModel.on_coa.for_entity_available(
                user_model=self.USER_MODEL,
                entity_slug=self.ENTITY_SLUG
            )

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
