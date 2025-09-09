"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.core.exceptions import ValidationError
from django.forms import (ModelForm, DateInput, TextInput, Select, CheckboxInput, modelformset_factory, Textarea,
                          DateTimeInput)
from django.forms.models import BaseModelFormSet
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_RECEIVABLES, LIABILITY_CL_DEFERRED_REVENUE
from django_ledger.models import (AccountModel, CustomerModel, InvoiceModel, ItemTransactionModel, ItemModel)
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class InvoiceModelCreateForEstimateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.get_customer_queryset()
        self.get_accounts_queryset()

    def get_customer_queryset(self):
        if 'customer' in self.fields:
            customer_qs = CustomerModel.objects.for_entity(
                entity_model=self.ENTITY_SLUG
            ).active()
            self.fields['customer'].queryset = customer_qs

    def get_accounts_queryset(self):

        if all([
            'cash_account' in self.fields,
            'prepaid_account' in self.fields,
            'unearned_account' in self.fields,
        ]):

            account_qs = AccountModel.objects.for_entity(
                entity_model=self.ENTITY_SLUG
            ).for_invoice()

            self.fields['cash_account'].queryset = account_qs.filter(role__exact=ASSET_CA_CASH)
            self.fields['prepaid_account'].queryset = account_qs.filter(role__exact=ASSET_CA_RECEIVABLES)
            self.fields['unearned_account'].queryset = account_qs.filter(role__exact=LIABILITY_CL_DEFERRED_REVENUE)

    class Meta:
        model = InvoiceModel
        fields = [
            'terms',
            'cash_account',
            'prepaid_account',
            'unearned_account'
        ]
        labels = {
            'terms': _('Invoice Terms'),
            'date_draft': _('Draft Date'),
            'unearned_account': _('Deferred Revenue Account'),
            'prepaid_account': _('Receivable Account')
        }
        widgets = {
            'customer': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'date_draft': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Invoice Date (YYYY-MM-DD)...'),
                'id': 'djl-invoice-draft-date-input'
            }),
            'amount_due': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': '$$$'}),
            'terms': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'cash_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'prepaid_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'unearned_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
        }


class InvoiceModelCreateForm(InvoiceModelCreateForEstimateForm):
    class Meta(InvoiceModelCreateForEstimateForm.Meta):
        fields = [
            'customer',
            'date_draft',
            'terms',
            'cash_account',
            'prepaid_account',
            'unearned_account'
        ]


class BaseInvoiceModelUpdateForm(ModelForm):

    def __init__(self,
                 *args,
                 entity_slug,
                 user_model,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.INVOICE_MODEL: InvoiceModel = self.instance

    class Meta:
        model = InvoiceModel
        fields = [
            'markdown_notes'
        ]
        labels = {
            'progress': _('Progress Amount 0.00 -> 1.00 (percent)'),
            'accrue': _('Will this Bill be Accrued?'),
            'amount_paid': _('Amount Received')
        }
        widgets = {
            'timestamp': DateTimeInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'terms': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'invoice_status': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'customer': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'date_paid': DateInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'placeholder': _('Paid Date (YYYY-MM-DD)...')}
            ),
            'amount_paid': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                }),
            'progress': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'accrue': CheckboxInput(attrs={'type': 'checkbox'}),
            'paid': CheckboxInput(attrs={'type': 'checkbox'}),
            'markdown_notes': Textarea(attrs={
                'class': 'textarea'
            })

        }


class DraftInvoiceModelUpdateForm(BaseInvoiceModelUpdateForm):
    class Meta(BaseInvoiceModelUpdateForm.Meta):
        fields = [
            'customer',
            'terms',
            'markdown_notes'
        ]


class InReviewInvoiceModelUpdateForm(BaseInvoiceModelUpdateForm):
    class Meta(BaseInvoiceModelUpdateForm.Meta):
        fields = [
            'markdown_notes'
        ]


class ApprovedInvoiceModelUpdateForm(BaseInvoiceModelUpdateForm):
    class Meta(BaseInvoiceModelUpdateForm.Meta):
        fields = [
            'amount_paid',
            'markdown_notes'
        ]


class AccruedAndApprovedInvoiceModelUpdateForm(BaseInvoiceModelUpdateForm):
    class Meta(BaseInvoiceModelUpdateForm.Meta):
        fields = [
            'progress',
            'amount_paid',
            'markdown_notes'
        ]


class PaidInvoiceModelUpdateForm(BaseInvoiceModelUpdateForm):
    class Meta(BaseInvoiceModelUpdateForm.Meta):
        fields = [
            'markdown_notes'
        ]


class InvoiceItemForm(ModelForm):

    def __init__(self,
                 *args,
                 entity_slug,
                 user_model,
                 invoice_model,
                 **kwargs):
        super(InvoiceItemForm, self).__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.INVOICE_MODEL = invoice_model

    def clean(self):
        cleaned_data = super(InvoiceItemForm, self).clean()
        quantity = cleaned_data['quantity']
        if self.instance.item_model_id:
            item_model: ItemModel = self.instance.item_model
            if item_model.for_inventory and quantity > item_model.inventory_received:
                raise ValidationError(f'Cannot invoice more than {item_model.inventory_received} units available.')
        return cleaned_data

    class Meta:
        model = ItemTransactionModel
        fields = [
            'item_model',
            'unit_cost',
            'quantity'
        ]
        widgets = {
            'item_model': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'unit_cost': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'quantity': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            })
        }


class BaseInvoiceItemTransactionFormset(BaseModelFormSet):

    def __init__(self, *args,
                 entity_slug,
                 user_model,
                 invoice_model,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.INVOICE_MODEL: InvoiceModel = invoice_model
        self.ENTITY_SLUG = entity_slug

        items_qs = ItemModel.objects.for_invoice(
            entity_model=self.ENTITY_SLUG
        )

        for form in self.forms:
            if not self.INVOICE_MODEL.can_edit_items():
                form.fields['item_model'].disabled = True
                form.fields['quantity'].disabled = True
                form.fields['unit_cost'].disabled = True
                form.can_delete = False
            form.fields['item_model'].queryset = items_qs

    def get_queryset(self):
        if not self.queryset:
            self.queryset = ItemTransactionModel.objects.for_invoice(
                entity_model=self.ENTITY_SLUG,
                invoice_pk=self.INVOICE_MODEL.uuid
            )
        else:
            self.queryset = self.INVOICE_MODEL.itemtransactionmodel_set.all()
        return self.queryset

    def get_form_kwargs(self, index):
        return {
            'entity_slug': self.ENTITY_SLUG,
            'user_model': self.USER_MODEL,
            'invoice_model': self.INVOICE_MODEL,
        }


def get_invoice_itemtxs_formset_class(invoice_model: InvoiceModel):
    can_delete = invoice_model.can_edit_items()
    return modelformset_factory(
        model=ItemTransactionModel,
        form=InvoiceItemForm,
        formset=BaseInvoiceItemTransactionFormset,
        can_delete=can_delete,
        extra=5 if can_delete else 0
    )
