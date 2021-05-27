"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.forms import (ModelForm, DateInput, TextInput, Select, BaseModelFormSet,
                          modelformset_factory)
from django.utils.translation import gettext_lazy as _

from django_ledger.models import (ItemModel, PurchaseOrderModel, PurchaseOrderItemThroughModel)
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

    #
    #     def save(self, commit=True):
    #         if commit:
    #             self.instance.migrate_state(
    #                 user_model=self.USER_MODEL,
    #                 entity_slug=self.ENTITY_SLUG
    #             )
    #         super().save(commit=commit)

    class Meta:
        model = PurchaseOrderModel
        fields = [
            'po_title',
            'po_status',
            'po_notes',
            'vendor',
            'fulfillment_date'
        ]

        widgets = {
            'po_title': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'po_status': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'vendor': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'fulfillment_date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Fulfillment Date (YYYY-MM-DD)...')
            }),
        }


class PurchaseOrderItemForm(ModelForm):
    class Meta:
        model = PurchaseOrderItemThroughModel
        fields = [
            'item_model',
            'unit_cost',
            'entity_unit',
            'quantity'
        ]
        widgets = {
            'item_model': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            }),
            'entity_unit': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
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


PurchaseOrderItemFormset = modelformset_factory(
    model=PurchaseOrderItemThroughModel,
    form=PurchaseOrderItemForm,
    formset=BasePurchaseOrderItemFormset,
    can_delete=True,
    extra=5
)
