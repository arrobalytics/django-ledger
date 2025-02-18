from django import forms
from django.forms import (
    ModelForm, BaseModelFormSet, modelformset_factory,
    Select, NumberInput, HiddenInput,
    TextInput, ValidationError
)
from django.utils.translation import gettext_lazy as _

from django_ledger.models import (
    StagedTransactionModel,
    ImportJobModel,
    EntityModel
)
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class ImportJobModelCreateForm(ModelForm):

    def __init__(self, entity_model: EntityModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_MODEL: EntityModel = entity_model
        self.fields['bank_account_model'].queryset = self.ENTITY_MODEL.bankaccountmodel_set.all().active()

    ofx_file = forms.FileField(
        label='Select File...',
        required=True,
        widget=forms.FileInput(
            attrs={
                'class': 'file-input',
                'accept': '.ofx,.qfx'
            })
    )

    class Meta:
        model = ImportJobModel
        fields = [
            'bank_account_model',
            'description',
        ]
        widgets = {
            'description': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                'placeholder': _('What\'s this import about?...')
            }),
            'bank_account_model': Select(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                }),
        }
        help_texts = {
            'bank_account_model': _('Select the bank account to import transactions from.'),
        }


class ImportJobModelUpdateForm(ModelForm):
    class Meta:
        model = ImportJobModel
        fields = [
            'description'
        ]
        widgets = {
            'description': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            })
        }


class StagedTransactionModelForm(ModelForm):
    tx_import = forms.BooleanField(initial=False, required=False)
    tx_split = forms.BooleanField(initial=False, required=False)

    def __init__(self, base_formset_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.BASE_FORMSET_INSTANCE = base_formset_instance

        # for IDE typing hints...
        instance: StagedTransactionModel = getattr(self, 'instance', None)

        # avoids multiple DB queries rendering the formset...
        self.fields['unit_model'].choices = self.BASE_FORMSET_INSTANCE.UNIT_MODEL_CHOICES

        # avoids multiple DB queries rendering the formset...
        self.fields['account_model'].choices = self.BASE_FORMSET_INSTANCE.ACCOUNT_MODEL_CHOICES

        if instance:
            if not instance.is_children():
                self.fields['amount_split'].widget = HiddenInput()
                self.fields['amount_split'].disabled = True
            else:
                self.fields['bundle_split'].widget = HiddenInput()
                self.fields['bundle_split'].disabled = True

            if not instance.can_have_account():
                self.fields['account_model'].widget = HiddenInput()
                self.fields['account_model'].disabled = True

            if not instance.can_have_unit():
                self.fields['unit_model'].widget = HiddenInput()
                self.fields['unit_model'].disabled = True

            if not instance.can_import():
                self.fields['tx_import'].widget = HiddenInput()
                self.fields['tx_import'].disabled = True
            if not instance.can_split():
                self.fields['tx_split'].widget = HiddenInput()
                self.fields['tx_split'].disabled = True

    def clean_account_model(self):
        staged_txs_model: StagedTransactionModel = self.instance
        if staged_txs_model.has_children():
            return None
        return self.cleaned_data['account_model']

    def clean_unit_model(self):
        staged_txs_model: StagedTransactionModel = self.instance
        if not staged_txs_model.can_have_unit():
            if staged_txs_model.parent_id:
                return staged_txs_model.parent.unit_model
        return self.cleaned_data['unit_model']

    def clean_tx_import(self):
        staged_txs_model: StagedTransactionModel = self.instance
        if staged_txs_model.is_children():
            return False
        return self.cleaned_data['tx_import']

    def clean(self):
        # cannot import and split at the same time
        if self.cleaned_data['tx_import'] and self.cleaned_data['tx_split']:
            raise ValidationError(message=_('Cannot import and split at the same time'))

    class Meta:
        model = StagedTransactionModel
        fields = [
            'tx_import',
            'bundle_split',
            'amount_split',
            'account_model',
            'unit_model'
        ]
        widgets = {
            'account_model': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'unit_model': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'amount_split': NumberInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small'
            })
        }


class BaseStagedTransactionModelFormSet(BaseModelFormSet):

    def __init__(self, *args,
                 entity_model: EntityModel,
                 import_job_model: ImportJobModel,
                 **kwargs):
        super().__init__(*args, **kwargs)

        # validates that the job import model belongs to the entity model...
        if import_job_model.entity_uuid != entity_model.uuid:
            raise ValidationError(message=_('Import job does not belong to this entity'))

        self.ENTITY_MODEL = entity_model
        self.IMPORT_JOB_MODEL: ImportJobModel = import_job_model
        self.MAPPED_ACCOUNT_MODEL = self.IMPORT_JOB_MODEL.bank_account_model.account_model

        self.account_model_qs = entity_model.get_coa_accounts().available().exclude(
            uuid__exact=self.MAPPED_ACCOUNT_MODEL.uuid
        )
        self.ACCOUNT_MODEL_CHOICES = [
            (a.uuid, a) if i > 0 else (None, '----') for i, a in
            enumerate(self.account_model_qs)
        ]

        self.unit_model_qs = entity_model.entityunitmodel_set.all()
        self.UNIT_MODEL_CHOICES = [
            (u.uuid, u) if i > 0 else (None, '----') for i, u in
            enumerate(self.unit_model_qs)
        ]
        self.queryset = self.IMPORT_JOB_MODEL.stagedtransactionmodel_set.all().is_pending()

    def get_form_kwargs(self, index):
        return {
            'base_formset_instance': self,
        }


StagedTransactionModelFormSet = modelformset_factory(
    model=StagedTransactionModel,
    form=StagedTransactionModelForm,
    formset=BaseStagedTransactionModelFormSet,
    can_delete=True,
    can_order=False,
    extra=0
)
