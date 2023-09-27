from django import forms
from django.forms import ModelForm, BaseModelFormSet, modelformset_factory, Select, NumberInput, HiddenInput

from django_ledger.models import StagedTransactionModel, AccountModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class OFXFileImportForm(forms.Form):
    ofx_file = forms.FileField(
        label='Select File...',
        widget=forms.FileInput(attrs={
            'class': 'file-input'
        }))


class StagedTransactionModelForm(ModelForm):
    tx_import = forms.BooleanField(initial=False, required=False)
    tx_split = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance: StagedTransactionModel = getattr(self, 'instance', None)
        if instance:

            if not instance.is_children():
                self.fields['amount_split'].widget = HiddenInput()

            if instance.has_children():
                self.fields['account_model'].widget = HiddenInput()

            if not instance.can_import():
                self.fields['tx_import'].disabled = True
                self.fields['tx_import'].widget = HiddenInput()
            if not instance.can_split():
                self.fields['tx_split'].disabled = True
                self.fields['tx_split'].widget = HiddenInput()


    def clean_account_model(self):
        staged_txs_model: StagedTransactionModel = self.instance
        if staged_txs_model.has_children():
            return None
        return self.cleaned_data['account_model']

    class Meta:
        model = StagedTransactionModel
        fields = [
            'tx_import',
            'amount_split',
            'account_model'
        ]
        widgets = {
            'account_model': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'amount_split': NumberInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small'
            })
        }


class BaseStagedTransactionModelFormSet(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, exclude_account=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.IMPORT_DISABLED = not exclude_account
        self.CASH_ACCOUNT = exclude_account

        accounts_qs = AccountModel.objects.for_entity_available(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG
        ).order_by('role', 'name')

        if exclude_account:
            accounts_qs = accounts_qs.exclude(uuid__exact=exclude_account.uuid)

        for form in self.forms:
            form.fields['account_model'].queryset = accounts_qs
            form.fields['account_model'].widget.attrs['disabled'] = self.IMPORT_DISABLED


StagedTransactionModelFormSet = modelformset_factory(
    model=StagedTransactionModel,
    form=StagedTransactionModelForm,
    formset=BaseStagedTransactionModelFormSet,
    can_delete=False,
    extra=0)
