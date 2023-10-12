from django import forms
from django.forms import (ModelForm, BaseModelFormSet, modelformset_factory, Select, NumberInput, HiddenInput,
                          TextInput,
                          ValidationError)
from django.utils.translation import gettext_lazy as _

from django_ledger.models import StagedTransactionModel, AccountModel, EntityUnitModel, ImportJobModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class ImportJobModelCreateForm(ModelForm):
    ofx_file = forms.FileField(
        label='Select File...',
        widget=forms.FileInput(
            attrs={
                'class': 'file-input'
            })
    )

    class Meta:
        model = ImportJobModel
        fields = [
            'description'
        ]
        widgets = {
            'description': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                'placeholder': _('What\'s this import about?...')
            })
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance: StagedTransactionModel = getattr(self, 'instance', None)
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
        model = StagedTransactionModel.objects.get_queryset().model
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

    def __init__(self, *args, entity_slug, user_model, exclude_account=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.IMPORT_DISABLED = not exclude_account
        self.CASH_ACCOUNT = exclude_account

        account_model_qs = AccountModel.objects.for_entity_available(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG
        ).order_by('role', 'name')

        unit_model_qs = EntityUnitModel.objects.for_entity(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG
        )

        if exclude_account:
            account_model_qs = account_model_qs.exclude(uuid__exact=exclude_account.uuid)

        for form in self.forms:
            form.fields['account_model'].queryset = account_model_qs
            form.fields['account_model'].widget.attrs['disabled'] = self.IMPORT_DISABLED
            form.fields['unit_model'].queryset = unit_model_qs

    # def get_queryset(self):


StagedTransactionModelFormSet = modelformset_factory(
    model=StagedTransactionModel,
    form=StagedTransactionModelForm,
    formset=BaseStagedTransactionModelFormSet,
    can_delete=True,
    can_delete_extra=0,
    can_order=False,
    extra=0)
