"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.forms import (ModelForm, DateInput, TextInput, Select, BaseModelFormSet,
                          modelformset_factory, Textarea, BooleanField, ValidationError)
from django.utils.translation import gettext_lazy as _

from django_ledger.models import (ItemModel, PurchaseOrderModel, ItemTransactionModel, EntityUnitModel)
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class PurchaseOrderModelCreateForm(ModelForm):
    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

    class Meta:
        model = PurchaseOrderModel
        fields = [
            'po_title',
        ]
        widgets = {
            'po_title': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                'placeholder': 'What this PO is about...'})
        }
        labels = {
            'for_inventory': _('Is this an inventory purchase?')
        }


class BasePurchaseOrderModelUpdateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.PO_MODEL: PurchaseOrderModel = self.instance

    class Meta:
        model = PurchaseOrderModel
        fields = [
            'markdown_notes'
        ]
        widgets = {
            'po_title': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large'
            }),
            'po_status': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'vendor': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'date_fulfilled': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Fulfillment Date (YYYY-MM-DD)...')
            }),
            'markdown_notes': Textarea(attrs={
                'class': 'textarea'
            })
        }
        labels = {
            'po_status': _('PO Status'),
            'fulfilled': _('Mark as Fulfilled'),
            'markdown_notes': _('PO Notes'),
        }


class DraftPurchaseOrderModelUpdateForm(BasePurchaseOrderModelUpdateForm):
    class Meta(BasePurchaseOrderModelUpdateForm.Meta):
        fields = [
            'po_title',
            'markdown_notes',
        ]


class ReviewPurchaseOrderModelUpdateForm(BasePurchaseOrderModelUpdateForm):
    class Meta(BasePurchaseOrderModelUpdateForm.Meta):
        fields = [
            'markdown_notes',
        ]


class ApprovedPurchaseOrderModelUpdateForm(BasePurchaseOrderModelUpdateForm):
    class Meta(BasePurchaseOrderModelUpdateForm.Meta):
        fields = [
            'markdown_notes',
        ]


class PurchaseOrderItemTransactionForm(ModelForm):
    create_bill = BooleanField(required=False)

    class Meta:
        model = ItemTransactionModel
        fields = [
            'item_model',
            'po_unit_cost',
            'po_quantity',
            'entity_unit',
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
            'po_unit_cost': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'po_quantity': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            })
        }

    def clean(self):
        cleaned_data = super(PurchaseOrderItemTransactionForm, self).clean()
        po_item_status = cleaned_data['po_item_status']
        po_item_model: ItemTransactionModel = self.instance
        if 'po_item_status' in self.changed_data:
            po_model: PurchaseOrderModel = getattr(self, 'PO_MODEL')
            if po_model.po_status == po_model.PO_STATUS_APPROVED:
                if not po_item_status:
                    raise ValidationError('Cannot assign null status to approved PO.')
                if all([
                    self.instance.bill_model_id,
                    po_item_status == ItemTransactionModel.STATUS_NOT_ORDERED
                ]):
                    raise ValidationError('Cannot assign not ordered status to a billed item. '
                                          'Void or delete bill first')
            if all([
                po_item_status in [ItemTransactionModel.STATUS_IN_TRANSIT, ItemTransactionModel.STATUS_RECEIVED],
                not po_item_model.bill_model_id
            ]):
                raise ValidationError(f'Cannot mark as {po_item_status.upper()}. '
                                      'Item must be billed first.')
        return cleaned_data


class BasePurchaseOrderItemFormset(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, po_model: PurchaseOrderModel, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.ENTITY_SLUG = entity_slug
        self.PO_MODEL = po_model

        items_qs = ItemModel.objects.for_po(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        unit_qs = EntityUnitModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        for form in self.forms:
            form.PO_MODEL = self.PO_MODEL
            form.fields['item_model'].queryset = items_qs
            form.fields['entity_unit'].queryset = unit_qs
            if not self.PO_MODEL.can_edit_items():
                form.fields['po_unit_cost'].disabled = True
                form.fields['po_quantity'].disabled = True
                form.fields['entity_unit'].disabled = True
                form.fields['item_model'].disabled = True
                if not self.PO_MODEL.is_approved() or self.PO_MODEL.is_fulfilled():
                    form.fields['po_item_status'].disabled = True
                    form.fields['po_item_status'].widget.attrs['class'] += form.instance.get_status_css_class()
            # PO is Draft
            else:
                form.fields['po_item_status'].disabled = True

    def get_queryset(self):
        po_item_queryset, _ = self.PO_MODEL.get_itemtxs_data()
        return po_item_queryset


CanEditPurchaseOrderItemFormset = modelformset_factory(
    model=ItemTransactionModel,
    form=PurchaseOrderItemTransactionForm,
    formset=BasePurchaseOrderItemFormset,
    can_delete=True,
    extra=5
)

ReadOnlyPurchaseOrderItemFormset = modelformset_factory(
    model=ItemTransactionModel,
    form=PurchaseOrderItemTransactionForm,
    formset=BasePurchaseOrderItemFormset,
    can_delete=False,
    extra=0
)


def get_po_itemtxs_formset_class(po_model: PurchaseOrderModel):
    if po_model.is_draft():
        return CanEditPurchaseOrderItemFormset
    return ReadOnlyPurchaseOrderItemFormset
