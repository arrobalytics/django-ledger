"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.forms import (ModelForm, DateInput, TextInput, Select, BaseModelFormSet,
                          modelformset_factory, Textarea, BooleanField, ValidationError)
from django.utils.translation import gettext_lazy as _

from django_ledger.models import (ItemModel, PurchaseOrderModel, ItemThroughModel, EntityUnitModel)
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

        if self.instance.po_status == PurchaseOrderModel.PO_STATUS_REVIEW:
            self.fields['po_date'].disabled = True
            self.fields['fulfillment_date'].disabled = True
            self.fields['fulfilled'].disabled = True
        elif self.instance.po_status == PurchaseOrderModel.PO_STATUS_APPROVED:
            self.fields['po_status'].disabled = True
            self.fields['po_date'].disabled = True
            if self.instance.fulfilled:
                self.fields['fulfilled'].disabled = True
                self.fields['fulfillment_date'].disabled = True
        # PO is Draft
        else:
            self.fields['fulfillment_date'].disabled = True
            self.fields['fulfilled'].disabled = True

    class Meta:
        model = PurchaseOrderModel
        fields = [
            'po_date',
            'po_title',
            'po_status',
            'markdown_notes',
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
            'markdown_notes': Textarea(attrs={
                'class': 'textarea'
            })
        }
        labels = {
            'po_status': _('PO Status'),
            'fulfilled': _('Mark as Fulfilled'),
            'markdown_notes': _('PO Notes')
        }

    def clean(self):
        cleaned_data = super(PurchaseOrderModelUpdateForm, self).clean()
        is_fulfilled = cleaned_data['fulfilled']
        new_status = cleaned_data['po_status']

        if 'fulfilled' in self.changed_data:
            if not is_fulfilled:
                raise ValidationError(
                    message=f'Cannot change status to un-fulfilled once fulfilled. Void instead.'
                )
            if new_status != PurchaseOrderModel.PO_STATUS_APPROVED:
                raise ValidationError(
                    message=f'Cannot fulfill a PO that has not been approved.'
                )

        if 'po_status' in self.changed_data:
            initial_status = self.initial['po_status']
            if initial_status == PurchaseOrderModel.PO_STATUS_APPROVED:
                raise ValidationError(
                    message=f'Cannot change form status to {new_status} '
                            f'from {initial_status}'
                )
        return cleaned_data


class PurchaseOrderItemForm(ModelForm):
    create_bill = BooleanField(required=False)

    class Meta:
        model = ItemThroughModel
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
        cleaned_data = super(PurchaseOrderItemForm, self).clean()
        po_item_status = cleaned_data['po_item_status']
        po_item_model: ItemThroughModel = self.instance
        if 'po_item_status' in self.changed_data:
            po_model: PurchaseOrderModel = getattr(self, 'PO_MODEL')
            if po_model.po_status == po_model.PO_STATUS_APPROVED:
                if not po_item_status:
                    raise ValidationError('Cannot assign null status to approved PO.')
                if all([
                    self.instance.bill_model_id,
                    po_item_status == ItemThroughModel.STATUS_NOT_ORDERED
                ]):
                    raise ValidationError('Cannot assign not ordered status to a billed item. '
                                          'Void or delete bill first')
            if all([
                po_item_status in [ItemThroughModel.STATUS_IN_TRANSIT, ItemThroughModel.STATUS_RECEIVED],
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
            if self.PO_MODEL.po_status in [
                PurchaseOrderModel.PO_STATUS_APPROVED,
                PurchaseOrderModel.PO_STATUS_REVIEW
            ]:
                form.fields['po_unit_cost'].disabled = True
                form.fields['po_quantity'].disabled = True
                form.fields['entity_unit'].disabled = True
                form.fields['item_model'].disabled = True
                if self.PO_MODEL.po_status != PurchaseOrderModel.PO_STATUS_APPROVED or self.PO_MODEL.fulfilled:
                    form.fields['po_item_status'].disabled = True
                    form.fields['po_item_status'].widget.attrs['class'] += form.instance.get_status_css_class()
            # PO is Draft
            else:
                form.fields['po_item_status'].disabled = True


def get_po_item_formset(po_model: PurchaseOrderModel):
    if po_model.po_status != PurchaseOrderModel.PO_STATUS_APPROVED:
        return modelformset_factory(
            model=ItemThroughModel,
            form=PurchaseOrderItemForm,
            formset=BasePurchaseOrderItemFormset,
            can_delete=True,
            extra=5
        )
    return modelformset_factory(
        model=ItemThroughModel,
        form=PurchaseOrderItemForm,
        formset=BasePurchaseOrderItemFormset,
        can_delete=False,
        extra=0
    )
