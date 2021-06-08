"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.forms import (ModelForm, DateInput, TextInput, Select, BaseModelFormSet,
                          modelformset_factory, Textarea, BooleanField, HiddenInput)
from django.utils.translation import gettext_lazy as _

from django_ledger.models import (ItemModel, PurchaseOrderModel, ItemThroughModel)
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class PurchaseOrderModelCreateForm(ModelForm):
    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

    class Meta:
        model = PurchaseOrderModel
        fields = [
            'po_date',
            'po_title',
            'for_inventory'
        ]
        widgets = {
            'po_date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('PO Date (YYYY-MM-DD)...')
            }),
            'po_title': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                'placeholder': 'What this PO is about...'})
        }
        labels = {
            'for_inventory': _('Is this an inventory purchase?')
        }


class PurchaseOrderModelUpdateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

    class Meta:
        model = PurchaseOrderModel
        fields = [
            'po_date',
            'po_title',
            'po_status',
            'po_notes',
            'vendor',
            'fulfillment_date',
            'fulfilled'
        ]

        widgets = {
            'po_title': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large'
            }),
            'po_status': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'vendor': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'fulfillment_date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Fulfillment Date (YYYY-MM-DD)...')
            }),
            'po_date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('PO Date (YYYY-MM-DD)...')
            }),
            'po_notes': Textarea(attrs={
                'class': 'textarea'
            })
        }
        labels = {
            'po_status': _('PO Status'),
            'fulfilled': _('Is Fulfilled?')
        }


class PurchaseOrderItemForm(ModelForm):
    create_bill = BooleanField(required=False)

    class Meta:
        model = ItemThroughModel
        fields = [
            'item_model',
            'unit_cost',
            'entity_unit',
            'quantity',
            'po_item_status',
            'create_bill',
        ]
        widgets = {
            'item_model': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'entity_unit': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'po_item_status': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'unit_cost': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            }),
            'quantity': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            })
        }


class BasePurchaseOrderItemFormset(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, po_model: PurchaseOrderModel, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.ENTITY_SLUG = entity_slug
        self.PO_MODEL = po_model

        if self.PO_MODEL.for_inventory:
            items_qs = ItemModel.objects.inventory(
                entity_slug=self.ENTITY_SLUG,
                user_model=self.USER_MODEL
            )
        else:
            items_qs = ItemModel.objects.expenses(
                entity_slug=self.ENTITY_SLUG,
                user_model=self.USER_MODEL
            )

        self.LN = len(items_qs)  # evaluate the QS and cache results...
        for form in self.forms:
            form.fields['item_model'].queryset = items_qs
            if self.PO_MODEL.po_status != PurchaseOrderModel.PO_STATUS_APPROVED:
                form.fields['po_item_status'].widget.attrs['disabled'] = True
            else:
                form.fields['po_item_status'].widget.attrs['class'] += form.instance.get_status_css_class()


PurchaseOrderItemFormset = modelformset_factory(
    model=ItemThroughModel,
    form=PurchaseOrderItemForm,
    formset=BasePurchaseOrderItemFormset,
    can_delete=True,
    extra=5
)
