from itertools import groupby
from typing import Optional
from uuid import UUID

from django import forms
from django.db.models import Q
from django.forms import (
    BaseModelFormSet,
    CheckboxInput,
    HiddenInput,
    ModelForm,
    NumberInput,
    Select,
    Textarea,
    TextInput,
    ValidationError,
    modelformset_factory,
)
from django.utils.translation import gettext_lazy as _

from django_ledger.io import GROUP_DEBT_PAYMENT, GROUP_EXPENSES, GROUP_INCOME, GROUP_TRANSFERS
from django_ledger.models import (
    EntityModel,
    ImportJobModel,
    StagedTransactionModel,
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
            'bank_account_model': _('Select the bank account to import transactions from.'),
        }


class ImportJobModelUpdateForm(ModelForm):
    class Meta:
        model = ImportJobModel
        fields = ['description']
        widgets = {'description': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES})}


class BaseStagedTransactionModelFormSet(BaseModelFormSet):
    def __init__(
            self,
            *args,
            entity_model: EntityModel,
            import_job_model: ImportJobModel,
            staged_tx_pk: Optional[UUID | StagedTransactionModel] = None,
            **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # validates that the job import model belongs to the entity model...
        if import_job_model.entity_uuid != entity_model.uuid:
            raise ValidationError(message=_('Import job does not belong to this entity'))

        self.ENTITY_MODEL = entity_model
        self.IMPORT_JOB_MODEL: ImportJobModel = import_job_model
        self.STAGED_TX_MODEL: Optional[UUID | StagedTransactionModel] = staged_tx_pk

        staged_txs_qs = self.IMPORT_JOB_MODEL.stagedtransactionmodel_set.select_related(
            'import_job',
            'import_job__ledger_model',
            'import_job__ledger_model__entity',
            'import_job__bank_account_model__account_model',
            'vendor_model',
            'customer_model',
            'unit_model',
        ).is_pending()

        if self.STAGED_TX_MODEL:
            if isinstance(self.STAGED_TX_MODEL, StagedTransactionModel):
                staged_txs_qs = staged_txs_qs.filter(
                    Q(uuid__exact=self.STAGED_TX_MODEL.uuid) | Q(parent__uuid__exact=self.STAGED_TX_MODEL.uuid)
                )
            elif isinstance(self.STAGED_TX_MODEL, UUID):
                staged_txs_qs = staged_txs_qs.filter(
                    Q(uuid__exact=self.STAGED_TX_MODEL) | Q(parent__uuid__exact=self.STAGED_TX_MODEL)
                )
            else:
                staged_txs_qs = staged_txs_qs.none()

        self.queryset = staged_txs_qs

        self.MAPPED_ACCOUNT_MODEL = self.IMPORT_JOB_MODEL.bank_account_model.account_model

        self.account_model_qs = (
            self.ENTITY_MODEL.get_coa_accounts().available().exclude(uuid__exact=self.MAPPED_ACCOUNT_MODEL.uuid)
        )
        self.ACCOUNT_MODEL_CHOICES = [(None, '----')] + [(a.uuid, a) for a in self.account_model_qs]
        self.ACCOUNT_MODEL_EXPENSES_CHOICES = [(None, '----')] + [
            (a.uuid, a) for a in self.account_model_qs if a.role in GROUP_EXPENSES
        ]
        self.ACCOUNT_MODEL_SALES_CHOICES = [(None, '----')] + [
            (a.uuid, a) for a in self.account_model_qs if a.role in GROUP_INCOME
        ]

        self.ACCOUNT_MODEL_TRANSFERS_CHOICES = [(None, '----')] + [
            (a.uuid, a) for a in self.account_model_qs if a.role in GROUP_TRANSFERS
        ]

        self.ACCOUNT_MODEL_DEBT_PAYMENT_CHOICES = [(None, '----')] + [
            (a.uuid, a) for a in self.account_model_qs if a.role in GROUP_DEBT_PAYMENT
        ]

        self.unit_model_qs = entity_model.entityunitmodel_set.all()
        self.UNIT_MODEL_CHOICES = [(None, '----')] + [(u.uuid, u) for i, u in enumerate(self.unit_model_qs)]

        self.VENDOR_MODEL_QS = entity_model.vendormodel_set.visible().order_by('vendor_name')
        self.CUSTOMER_MODEL_QS = entity_model.customermodel_set.visible().order_by('customer_name')

        self.VENDOR_CHOICES = [(None, '-----')] + [(str(v.uuid), v) for v in self.VENDOR_MODEL_QS]
        self.CUSTOMER_CHOICES = [(None, '-----')] + [(str(c.uuid), c) for c in self.CUSTOMER_MODEL_QS]

        self.VENDOR_MAP = dict(self.VENDOR_CHOICES)
        self.CUSTOMER_MAP = dict(self.CUSTOMER_CHOICES)

        self.FORMS_BY_ID = {
            f.instance.uuid: f for f in self.forms if getattr(f, 'instance', None) and getattr(f.instance, 'uuid', None)
        }

        form_children = [(f.instance.parent_id, f.instance.uuid) for f in self.forms if f.instance.parent_id]
        form_children.sort(key=lambda f: f[0])

        self.FORM_CHILDREN = {g: list(j[1] for j in p) for g, p in groupby(form_children, key=lambda i: i[0])}

    def get_form_kwargs(self, index):
        return {
            'base_formset_instance': self,
            'entity_model': self.ENTITY_MODEL,
            'import_job_model': self.IMPORT_JOB_MODEL,
        }


class StagedTransactionModelForm(ModelForm):
    tx_import = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'is-checkradio',
            }
        ),
        label=_('Import Transaction'),
        help_text=_('Will import this transaction when saved...'),
    )

    tx_split = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'is-checkradio',
            }
        ),
        label=_('Add a Transaction Split?'),
        help_text=_('Will split this transaction when saved...'),
    )

    account_search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
                'data-account-search': None,
                'placeholder': _('Search Account...'),
            }
        ),
        label=_('Search Account...'),
        help_text=_('Filters the account list...'),
    )

    def __init__(
            self,
            *args,
            entity_model: EntityModel,
            import_job_model: ImportJobModel,
            base_formset_instance: BaseStagedTransactionModelFormSet,
            **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.ENTITY_MODEL: EntityModel = entity_model
        self.IMPORT_JOB_MODEL: ImportJobModel = import_job_model
        self.BASE_FORMSET: BaseStagedTransactionModelFormSet = base_formset_instance

        self.ACCOUNT_MODEL_CHOICES = self.BASE_FORMSET.ACCOUNT_MODEL_CHOICES
        self.EXPENSE_ACCOUNT_CHOICES = self.BASE_FORMSET.ACCOUNT_MODEL_EXPENSES_CHOICES
        self.SALES_ACCOUNT_CHOICES = self.BASE_FORMSET.ACCOUNT_MODEL_SALES_CHOICES
        self.TRANSFER_ACCOUNT_CHOICES = self.BASE_FORMSET.ACCOUNT_MODEL_TRANSFERS_CHOICES
        self.DEBT_PAYDOWN_ACCOUNT_CHOICES = self.BASE_FORMSET.ACCOUNT_MODEL_DEBT_PAYMENT_CHOICES
        self.UNIT_MODEL_CHOICES = self.BASE_FORMSET.UNIT_MODEL_CHOICES
        self.VENDOR_CHOICES = self.BASE_FORMSET.VENDOR_CHOICES
        self.CUSTOMER_CHOICES = self.BASE_FORMSET.CUSTOMER_CHOICES

        self.VENDOR_MAP = dict(self.VENDOR_CHOICES)
        self.CUSTOMER_MAP = dict(self.CUSTOMER_CHOICES)

        self.fields['vendor_model'].choices = self.VENDOR_CHOICES
        self.fields['customer_model'].choices = self.CUSTOMER_CHOICES
        self.fields['account_model'].choices = self.ACCOUNT_MODEL_CHOICES
        self.fields['unit_model'].choices = self.UNIT_MODEL_CHOICES

        self.fields['activity'].disabled = True

        staged_tx_model: StagedTransactionModel = getattr(self, 'instance', None)

        if staged_tx_model:
            if not staged_tx_model.can_have_activity():
                self.fields['activity'].widget = HiddenInput()

            if staged_tx_model.is_sales():
                self.fields['account_model'].choices = self.SALES_ACCOUNT_CHOICES
            if staged_tx_model.is_expense():
                self.fields['account_model'].choices = self.EXPENSE_ACCOUNT_CHOICES
            if staged_tx_model.is_transfer():
                self.fields['account_model'].choices = self.TRANSFER_ACCOUNT_CHOICES
            if staged_tx_model.is_debt_payment():
                self.fields['account_model'].choices = self.DEBT_PAYDOWN_ACCOUNT_CHOICES

            if not staged_tx_model.can_match():
                self.fields['matched_transaction'].widget = HiddenInput()
                self.fields['matched_transaction'].disabled = True

            candidates_qs = staged_tx_model.get_match_candidates_qs()

            if any([staged_tx_model.is_transfer(), staged_tx_model.is_debt_payment()]) and candidates_qs.exists():
                self.fields['matched_transaction_model'].queryset = candidates_qs
                if candidates_qs.count() == 1:
                    self.fields['matched_transaction_model'].initial = candidates_qs.first()
            else:
                self.fields['matched_transaction_model'].widget = HiddenInput()
                self.fields['matched_transaction_model'].disabled = True

            if staged_tx_model.has_match():
                self.fields['account_model'].disabled = True
                self.fields['account_search'].disabled = True

                self.fields['tx_split'].widget = HiddenInput()
                self.fields['tx_split'].disabled = True

                self.fields['vendor_model'].disabled = False
                self.fields['vendor_model'].widget = HiddenInput()
                self.fields['customer_model'].disabled = False
                self.fields['customer_model'].widget = HiddenInput()
            else:
                self.fields['matched_transaction'].disabled = False
                self.fields['matched_transaction'].widget = HiddenInput()

            if not staged_tx_model.has_children():
                self.fields['bundle_split'].widget = HiddenInput()
                self.fields['bundle_split'].disabled = True

            if not staged_tx_model.can_have_amount_split():
                self.fields['amount_split'].widget = HiddenInput()
                self.fields['amount_split'].disabled = True

            if not staged_tx_model.can_have_bundle_split():
                self.fields['bundle_split'].widget = HiddenInput()
                self.fields['bundle_split'].disabled = True

            if not staged_tx_model.can_have_receipt():
                self.fields['receipt_type'].widget = HiddenInput()
                self.fields['receipt_type'].disabled = True

            if not staged_tx_model.can_have_account():
                self.fields['account_model'].widget = HiddenInput()
                self.fields['account_model'].disabled = True

                self.fields['account_search'].widget = HiddenInput()
                self.fields['account_search'].disabled = True

            if not staged_tx_model.can_have_unit():
                self.fields['unit_model'].widget = HiddenInput()
                self.fields['unit_model'].disabled = True

            if not staged_tx_model.can_have_vendor():
                self.fields['vendor_model'].widget = HiddenInput()
                self.fields['vendor_model'].disabled = True

            if not staged_tx_model.can_have_customer():
                self.fields['customer_model'].widget = HiddenInput()
                self.fields['customer_model'].disabled = True

            if not staged_tx_model.can_import():
                self.fields['tx_import'].widget = HiddenInput()
                self.fields['tx_import'].disabled = True

            if not staged_tx_model.can_split():
                self.fields['tx_split'].widget = HiddenInput()
                self.fields['tx_split'].disabled = True

            if staged_tx_model.is_children():
                if 'tx_import' in self.fields:
                    self.fields['tx_import'].widget = HiddenInput()
                    self.fields['tx_import'].disabled = True
                if 'tx_split' in self.fields:
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

    def clean_bundle_split(self):
        staged_txs_model: StagedTransactionModel = self.instance
        if staged_txs_model.is_single():
            return True
        if staged_txs_model.is_children():
            return staged_txs_model.parent.bundle_split
        return self.cleaned_data['bundle_split']

    def clean_activity(self):
        return self.instance.activity

    def clean(self):
        # Prevent conflicting actions
        if self.cleaned_data.get('tx_import') and self.cleaned_data.get('tx_split'):
            raise ValidationError(message=_('Cannot import and split at the same time'))

        staged_txs_model: StagedTransactionModel = self.instance

        # Matching validation for transfers & debt payments
        if all(
                [
                    self.cleaned_data.get('matched_transaction') is True,
                    any([staged_txs_model.is_transfer(), staged_txs_model.is_debt_payment()]),
                ]
        ):
            candidates_qs = staged_txs_model.get_match_candidates_qs()
            selected = self.cleaned_data.get('matched_transaction_model')
            if candidates_qs.count() > 1 and selected is None:
                raise ValidationError(message=_('Multiple matches found. Please select a transaction to match.'))
            if candidates_qs.count() == 1 and selected is None:
                self.cleaned_data['matched_transaction_model'] = candidates_qs.first()

    class Meta:
        model = StagedTransactionModel
        fields = [
            'activity',
            'matched_transaction_model',
            'account_search',
            'account_model',
            'amount_split',
            'unit_model',
            'receipt_type',
            'vendor_model',
            'customer_model',
            'notes',
            'bundle_split',
            'matched_transaction',
            'tx_import',
        ]
        labels = {
            'bundle_split': _('Grouped Transactions'),
            'unit_model': _('Assigned Unit or Class'),
            'amount_split': _('Split Amount'),
            'account_model': _('Map to Account'),
            'matched_transaction': _('Match Transaction'),
            'vendor_model': _('Vendor'),
            'customer_model': _('Customer'),
        }
        help_texts = {
            'bundle_split': _('If checked, maps all splits to the same unit & receipt.'),
            'amount_split': _('All splits amount must total parent transaction amount.'),
            'account_model': _('The CoA account where the transaction will be imported.'),
            'matched_transaction': _('The transaction will be matched against the selected transaction.'),
        }
        widgets = {
            'account_model': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'unit_model': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'amount_split': NumberInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'vendor_model': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'customer_model': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'receipt_type': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'matched_transaction_model': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'notes': Textarea(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'activity': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'bundle_split': CheckboxInput(attrs={'class': 'is-checkradio'}),
        }


StagedTransactionModelFormSet = modelformset_factory(
    model=StagedTransactionModel,
    form=StagedTransactionModelForm,
    formset=BaseStagedTransactionModelFormSet,
    can_delete=True,
    can_order=False,
    extra=0,
)
