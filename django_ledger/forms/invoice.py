"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.forms import ModelForm, DateInput, TextInput, Select, CheckboxInput, modelformset_factory
from django.forms.models import BaseModelFormSet
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_DEFERRED_REVENUE
from django_ledger.models import (AccountModel, CustomerModel, InvoiceModel, ItemThroughModel, ItemModel)
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES
from django.core.exceptions import ValidationError


class InvoiceModelCreateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

        account_qs = AccountModel.on_coa.for_invoice(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG)

        # forcing evaluation of qs to cache results for fields... (avoids 4 database queries, vs 1)
        len(account_qs)

        self.fields['cash_account'].queryset = account_qs.filter(role__exact=ASSET_CA_CASH)
        self.fields['prepaid_account'].queryset = account_qs.filter(role__exact=ASSET_CA_PREPAID)
        self.fields['unearned_account'].queryset = account_qs.filter(role__exact=LIABILITY_CL_DEFERRED_REVENUE)

        customer_qs = CustomerModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )
        self.fields['customer'].queryset = customer_qs

    class Meta:
        model = InvoiceModel
        fields = [
            'customer',
            'date',
            'terms',
            'cash_account',
            'prepaid_account',
            'unearned_account'
        ]
        labels = {
            'terms': _('Invoice Terms')
        }
        widgets = {
            'customer': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),

            'date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Invoice Date (YYYY-MM-DD)...')
            }),
            'amount_due': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': '$$$'}),
            'terms': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small'
            }),

            'cash_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'prepaid_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'unearned_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),

        }


class InvoiceModelUpdateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

    class Meta:
        model = InvoiceModel
        fields = [
            'amount_paid',
            'paid',
            'paid_date',
            'progress',
            'accrue'
        ]
        labels = {
            'progress': _('Progress Amount 0.00 -> 1.00 (percent)'),
            'amount_paid': _('Amount Received')
        }
        widgets = {
            'date': DateInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'terms': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'paid_date': DateInput(
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

        }


class InvoiceItemForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model,
                 invoice_model, invoice_pk=None, **kwargs):
        super(InvoiceItemForm, self).__init__(*args, **kwargs)

        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.INVOICE_MODEL = invoice_model
        self.INVOICE_PK = invoice_pk

        if not self.instance.item_model_id:
            self.fields['unit_cost'].disabled = True
            self.fields['quantity'].disabled = True

    def clean(self):
        cleaned_data = super(InvoiceItemForm, self).clean()
        quantity = cleaned_data['quantity']
        if self.instance.item_model_id:
            item_model: ItemModel = self.instance.item_model
            if quantity > item_model.inventory_received:
                raise ValidationError(f'Cannot invoice more than {item_model.inventory_received} units available.')
        return cleaned_data

    class Meta:
        model = ItemThroughModel
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


class BaseInvoiceItemFormset(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model,
                 invoice_model=None, invoice_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not invoice_model and not invoice_pk:
            raise ValidationError('Must instantiate BaseInvoiceItemFormset with either invoice_model or invoice_pk')
        self.USER_MODEL = user_model
        self.INVOICE_MODEL: InvoiceModel = invoice_model
        self.INVOICE_PK = invoice_pk
        self.ENTITY_SLUG = entity_slug

        items_qs = ItemModel.objects.products_and_services(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        self.LN = len(items_qs)  # evaluate the QS and cache results...
        for form in self.forms:
            form.fields['item_model'].queryset = items_qs

    def get_queryset(self):
        if not self.queryset:
            if self.INVOICE_PK:
                self.queryset = ItemThroughModel.objects.for_invoice(
                    entity_slug=self.ENTITY_SLUG,
                    user_model=self.USER_MODEL,
                    invoice_pk=self.INVOICE_PK
                )
            else:
                self.queryset = self.INVOICE_MODEL.itemthroughmodel_set.all()
        return self.queryset

    def get_form_kwargs(self, index):
        return {
            'entity_slug': self.ENTITY_SLUG,
            'user_model': self.USER_MODEL,
            'invoice_pk': self.INVOICE_PK,
            'invoice_model': self.INVOICE_MODEL,
        }


InvoiceItemFormset = modelformset_factory(
    model=ItemThroughModel,
    form=InvoiceItemForm,
    formset=BaseInvoiceItemFormset,
    can_delete=True,
    extra=5
)
