from django import forms
from django.forms import ModelForm, BaseModelFormSet, modelformset_factory, Select, HiddenInput

from django_ledger.models import StagedTransactionModel, AccountModel, ImportJobModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class OFXFileImportForm(forms.Form):
    ofx_file = forms.FileField(widget=forms.FileInput(attrs={
        'class': 'input'
    }))


class StagedTransactionModelForm(ModelForm):
    import_tx = forms.BooleanField(initial=False, required=False)

    class Meta:
        model = StagedTransactionModel
        fields = [
            'date_posted',
            'name',
            'amount',
            'earnings_account',
            'import_tx',
            'import_job'
        ]
        widgets = {
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
                'readonly': True
            })
        }


class BaseStagedTransactionModelFormSet(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

        accounts_qs = AccountModel.on_coa.for_entity_available(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG
        )

        import_job_qs = ImportJobModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        for form in self.forms:
            form.fields['earnings_account'].queryset = accounts_qs
            form.fields['import_job'].queryset = import_job_qs


StagedTransactionModelFormSet = modelformset_factory(
    model=StagedTransactionModel,
    form=StagedTransactionModelForm,
    formset=BaseStagedTransactionModelFormSet,
    can_delete=False,
    extra=0)
