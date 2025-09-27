from django import forms
from django.forms import (
    ModelForm,
    BaseModelFormSet,
    modelformset_factory,
    Select,
    NumberInput,
    HiddenInput,
    TextInput,
    ValidationError,
)
from django.utils.translation import gettext_lazy as _

from django_ledger.io import GROUP_EXPENSES, GROUP_INCOME
from django_ledger.models import (
    StagedTransactionModel,
    ImportJobModel,
    EntityModel,
)
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class ImportJobModelCreateForm(ModelForm):
    def __init__(self, entity_model: EntityModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_MODEL: EntityModel = entity_model
        self.fields[
            'bank_account_model'
        ].queryset = self.ENTITY_MODEL.bankaccountmodel_set.all().active()

    ofx_file = forms.FileField(
        label='Select File...',
        required=True,
        widget=forms.FileInput(attrs={'class': 'file-input', 'accept': '.ofx,.qfx'}),
    )

    class Meta:
        model = ImportJobModel
        fields = [
            'bank_account_model',
            'description',
        ]
        widgets = {
            'description': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                    'placeholder': _('Name this import...'),
                }
            ),
            'bank_account_model': Select(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                }
            ),
        }
        help_texts = {
            'bank_account_model': _(
                'Select the bank account to import transactions from.'
            ),
        }


class ImportJobModelUpdateForm(ModelForm):
    class Meta:
        model = ImportJobModel
        fields = ['description']
        widgets = {
            'description': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES})
        }


class StagedTransactionModelForm(ModelForm):
    tx_import = forms.BooleanField(initial=False, required=False)
    tx_split = forms.BooleanField(initial=False, required=False)

    def __init__(self, base_formset_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.BASE_FORMSET_INSTANCE: 'BaseStagedTransactionModelFormSet' = (
            base_formset_instance
        )
        self.VENDOR_CHOICES = self.BASE_FORMSET_INSTANCE.VENDOR_CHOICES
        self.VENDOR_MAP = self.BASE_FORMSET_INSTANCE.VENDOR_MAP

        self.CUSTOMER_CHOICES = self.BASE_FORMSET_INSTANCE.CUSTOMER_CHOICES
        self.CUSTOMER_MAP = self.BASE_FORMSET_INSTANCE.CUSTOMER_MAP

        self.EXPENSE_ACCOUNT_CHOICES = (
            self.BASE_FORMSET_INSTANCE.ACCOUNT_MODEL_EXPENSES_CHOICES
        )
        self.SALES_ACCOUNT_CHOICES = (
            self.BASE_FORMSET_INSTANCE.ACCOUNT_MODEL_SALES_CHOICES
        )
        self.SHOW_VENDOR_FIELD: bool = False
        self.SHOW_CUSTOMER_FIELD: bool = False

        staged_tx_model: StagedTransactionModel = getattr(self, 'instance', None)

        if staged_tx_model.can_migrate_receipt():
            if staged_tx_model.is_expense():
                self.fields['customer_model'].widget = forms.HiddenInput()
                self.fields['vendor_model'].choices = self.VENDOR_CHOICES
                self.fields['account_model'].choices = self.EXPENSE_ACCOUNT_CHOICES
                self.SHOW_VENDOR_FIELD = True
            elif staged_tx_model.is_sales():
                self.fields['vendor_model'].widget = forms.HiddenInput()
                self.fields['customer_model'].choices = self.CUSTOMER_CHOICES
                self.fields['account_model'].choices = self.SALES_ACCOUNT_CHOICES
                self.SHOW_CUSTOMER_FIELD = True
        else:
            self.fields['customer_model'].widget = forms.HiddenInput()
            self.fields['vendor_model'].widget = forms.HiddenInput()
            # avoids multiple DB queries rendering the formset...
            self.fields[
                'account_model'
            ].choices = self.BASE_FORMSET_INSTANCE.ACCOUNT_MODEL_CHOICES

        # avoids multiple DB queries rendering the formset...
        self.fields[
            'unit_model'
        ].choices = self.BASE_FORMSET_INSTANCE.UNIT_MODEL_CHOICES

        if staged_tx_model:
            if not staged_tx_model.is_children():
                self.fields['amount_split'].widget = HiddenInput()
                self.fields['amount_split'].disabled = True
            else:
                self.fields['bundle_split'].widget = HiddenInput()
                self.fields['bundle_split'].disabled = True

            if staged_tx_model.has_children():
                self.fields['receipt_type'].widget = HiddenInput()
                self.fields['receipt_type'].disabled = True

            if not staged_tx_model.can_have_account():
                self.fields['account_model'].widget = HiddenInput()
                self.fields['account_model'].disabled = True

            if not staged_tx_model.can_have_unit():
                self.fields['unit_model'].widget = HiddenInput()
                self.fields['unit_model'].disabled = True

            # receipt-related field visibility: not allowed for children rows
            if staged_tx_model.is_children():
                for f in [
                    'receipt_type',
                    'vendor_model',
                    'customer_model',
                    'bundle_split',
                ]:
                    self.fields[f].widget = HiddenInput()
                    self.fields[f].disabled = True

            if staged_tx_model.is_single():
                self.fields['bundle_split'].widget = HiddenInput()
                self.fields['bundle_split'].disabled = True

            if not staged_tx_model.can_migrate():
                self.fields['tx_import'].widget = HiddenInput()
                self.fields['tx_import'].disabled = True

            if not staged_tx_model.can_split():
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
            if staged_txs_model.is_children():
                return staged_txs_model.parent.unit_model
            return None
        return self.cleaned_data['unit_model']

    def clean_tx_import(self):
        staged_txs_model: StagedTransactionModel = self.instance
        if staged_txs_model.is_children():
            return False
        return self.cleaned_data['tx_import']

    def clean(self):
        if self.cleaned_data['tx_import'] and self.cleaned_data['tx_split']:
            raise ValidationError(message=_('Cannot import and split at the same time'))

        staged_txs_model: StagedTransactionModel = self.instance
        if all(
            [
                staged_txs_model.has_children(),
                staged_txs_model.has_receipt(),
                not staged_txs_model.bundle_split,
            ]
        ):
            raise ValidationError(
                message=_(
                    'Receipt transactions cannot be split into multiple receipts.'
                )
            )

    class Meta:
        model = StagedTransactionModel
        fields = [
            'tx_import',
            'bundle_split',
            'amount_split',
            'account_model',
            'unit_model',
            'receipt_type',
            'vendor_model',
            'customer_model',
        ]
        widgets = {
            'account_model': Select(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
                }
            ),
            'unit_model': Select(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
                }
            ),
            'amount_split': NumberInput(
                attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small'}
            ),
            'vendor_model': Select(
                attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small'}
            ),
            'customer_model': Select(
                attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small'}
            ),
            'receipt_type': Select(
                attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small'}
            ),
        }


class BaseStagedTransactionModelFormSet(BaseModelFormSet):
    def __init__(
        self,
        *args,
        entity_model: EntityModel,
        import_job_model: ImportJobModel,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # validates that the job import model belongs to the entity model...
        if import_job_model.entity_uuid != entity_model.uuid:
            raise ValidationError(
                message=_('Import job does not belong to this entity')
            )

        self.ENTITY_MODEL = entity_model
        self.IMPORT_JOB_MODEL: ImportJobModel = import_job_model

        self.queryset = (
            self.IMPORT_JOB_MODEL.stagedtransactionmodel_set.all().is_pending()
        )

        self.MAPPED_ACCOUNT_MODEL = (
            self.IMPORT_JOB_MODEL.bank_account_model.account_model
        )

        self.account_model_qs = (
            entity_model.get_coa_accounts()
            .available()
            .exclude(uuid__exact=self.MAPPED_ACCOUNT_MODEL.uuid)
        )
        self.ACCOUNT_MODEL_CHOICES = [(None, '----')] + [
            (a.uuid, a) for a in self.account_model_qs
        ]
        self.ACCOUNT_MODEL_EXPENSES_CHOICES = [(None, '----')] + [
            (a.uuid, a) for a in self.account_model_qs if a.role in GROUP_EXPENSES
        ]
        self.ACCOUNT_MODEL_SALES_CHOICES = [(None, '----')] + [
            (a.uuid, a) for a in self.account_model_qs if a.role in GROUP_INCOME
        ]

        self.unit_model_qs = entity_model.entityunitmodel_set.all()
        self.UNIT_MODEL_CHOICES = [
            (u.uuid, u) if i > 0 else (None, '----')
            for i, u in enumerate(self.unit_model_qs)
        ]

        self.VENDOR_MODEL_QS = entity_model.vendormodel_set.visible()
        len(self.VENDOR_MODEL_QS)
        self.CUSTOMER_MODEL_QS = entity_model.customermodel_set.visible()
        len(self.CUSTOMER_MODEL_QS)

        self.VENDOR_CHOICES = [(None, '-----')] + [
            (str(v.uuid), v) for v in self.VENDOR_MODEL_QS
        ]
        self.CUSTOMER_CHOICES = [(None, '-----')] + [
            (str(c.uuid), c) for c in self.CUSTOMER_MODEL_QS
        ]

        self.VENDOR_MAP = dict(self.VENDOR_CHOICES)
        self.CUSTOMER_MAP = dict(self.CUSTOMER_CHOICES)

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
    extra=0,
)
