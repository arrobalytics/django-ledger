from django import forms
from django.forms import ModelForm, BaseModelFormSet, modelformset_factory, Select, HiddenInput, ValidationError

from django_ledger.models import StagedTransactionModel, AccountModel, ImportJobModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class OFXFileImportForm(forms.Form):
    ofx_file = forms.FileField(
        label='Select File...',
        widget=forms.FileInput(attrs={
            'class': 'file-input'
        }))


class StagedTransactionModelForm(ModelForm):
    tx_import = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance:
            if instance.earnings_account and instance.tx:
                self.fields['earnings_account'].widget.attrs['disabled'] = True
                self.fields['earnings_account'].widget.attrs['value'] = instance.earnings_account
                self.fields['tx_import'].widget.attrs['disabled'] = True
                self.fields['tx_import'].widget.attrs['value'] = True
            elif not instance.earnings_account:
                self.fields['tx_import'].widget.attrs['disabled'] = True
            elif instance.earnings_account and not instance.tx:
                self.fields['tx_import'].widget.attrs['disabled'] = False

    class Meta:
        model = StagedTransactionModel
        fields = [
            'tx_import',
            'date_posted',
            'name',
            'amount',
            'earnings_account',
            'import_job',
            'tx'
        ]
        widgets = {
            'tx': HiddenInput(attrs={
                'readonly': True
            }),
            'date_posted': HiddenInput(attrs={
                'readonly': True
            }),
            'import_job': HiddenInput(attrs={
                'readonly': True
            }),
            'name': HiddenInput(attrs={
                'readonly': True
            }),
            'amount': HiddenInput(attrs={
                'readonly': True
            }),
            'earnings_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            })
        }

    def clean(self):
        earnings_account = self.cleaned_data['earnings_account']
        tx = self.cleaned_data['tx']

        if tx and not earnings_account:
            raise ValidationError('If tx, ea must be present.')


class BaseStagedTransactionModelFormSet(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, cash_account=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.IMPORT_DISABLED = not cash_account
        self.CASH_ACCOUNT = cash_account

        if cash_account:
            accounts_qs = AccountModel.on_coa.for_entity_available(
                user_model=self.USER_MODEL,
                entity_slug=self.ENTITY_SLUG
            ).exclude(uuid__exact=cash_account.uuid)
        else:
            accounts_qs = AccountModel.on_coa.none()

        import_job_qs = ImportJobModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        for form in self.forms:
            form.fields['earnings_account'].queryset = accounts_qs
            form.fields['earnings_account'].widget.attrs['disabled'] = self.IMPORT_DISABLED
            form.fields['import_job'].queryset = import_job_qs


StagedTransactionModelFormSet = modelformset_factory(
    model=StagedTransactionModel,
    form=StagedTransactionModelForm,
    formset=BaseStagedTransactionModelFormSet,
    can_delete=False,
    extra=0)
