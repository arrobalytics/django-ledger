from django import forms
from django.forms import ModelForm, BaseModelFormSet, modelformset_factory, Select, CheckboxInput

from django_ledger.models import StagedTransactionModel, AccountModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class OFXFileImportForm(forms.Form):
    ofx_file = forms.FileField(widget=forms.FileInput(attrs={
        'class': 'input'
    }))


class StagedTransactionModelForm(ModelForm):

    import_tx = forms.BooleanField()

    class Meta:
        model = StagedTransactionModel
        fields = [
            'date_posted',
            'name',
            'amount',
            'earnings_account',
            'import_tx'
        ]
        widgets = {
            'earnings_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small'
            })
        }


class BaseStagedTransactionModelFormSet(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, job_pk, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.JOB_PK = job_pk
        for form in self.forms:
            form.fields['earnings_account'].queryset = AccountModel.on_coa.for_entity_available(
                user_model=self.USER_MODEL,
                entity_slug=self.ENTITY_SLUG
            )


StagedTransactionModelFormSet = modelformset_factory(
    model=StagedTransactionModel,
    form=StagedTransactionModelForm,
    formset=BaseStagedTransactionModelFormSet,
    can_delete=False,
    extra=0)