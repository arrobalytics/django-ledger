"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""
from django.forms import (ModelForm, DateInput, TextInput, Select, CheckboxInput, BaseModelFormSet,
                          modelformset_factory)
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_DEFERRED_REVENUE
from django_ledger.models import (ItemModel, AccountModel, BillModel, BillModelItemsThroughModel,
                                  VendorModel, PurchaseOrderModel)
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

# class BillModelUpdateForm(ModelForm):
#
#     def __init__(self, *args, entity_slug, user_model, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.ENTITY_SLUG = entity_slug
#         self.USER_MODEL = user_model
#
#     def save(self, commit=True):
#         if commit:
#             self.instance.migrate_state(
#                 user_model=self.USER_MODEL,
#                 entity_slug=self.ENTITY_SLUG
#             )
#         super().save(commit=commit)
#
#     class Meta:
#         model = BillModel
#         fields = [
#             'xref',
#             'amount_due',
#             'amount_paid',
#             'paid',
#             'paid_date',
#             'progress',
#             'accrue'
#         ]
#         widgets = {
#             'xref': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
#                                      'placeholder': 'External Reference...'}),
#             'date': DateInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
#             'amount_due': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES, 'placeholder': '$$$'}),
#             'terms': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
#             'paid_date': DateInput(
#                 attrs={
#                     'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
#                     'placeholder': _('Date (YYYY-MM-DD)...')}
#             ),
#             'amount_paid': TextInput(
#                 attrs={
#                     'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
#                 }),
#             'progress': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
#             'accrue': CheckboxInput(attrs={'type': 'checkbox'}),
#             'paid': CheckboxInput(attrs={'type': 'checkbox'}),
#         }
#
#
# class BillItemForm(ModelForm):
#     class Meta:
#         model = BillModelItemsThroughModel
#         fields = [
#             'item_model',
#             'unit_cost',
#             'entity_unit',
#             'quantity'
#         ]
#         widgets = {
#             'item_model': Select(attrs={
#                 'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
#             }),
#             'entity_unit': Select(attrs={
#                 'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
#             }),
#             'unit_cost': TextInput(attrs={
#                 'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
#             }),
#             'quantity': TextInput(attrs={
#                 'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
#             })
#         }
#
#
# class BaseInvoiceItemFormset(BaseModelFormSet):
#
#     def __init__(self, *args, entity_slug, bill_pk, user_model, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.USER_MODEL = user_model
#         self.BILL_PK = bill_pk
#         self.ENTITY_SLUG = entity_slug
#
#         items_qs = ItemModel.objects.expenses(
#             entity_slug=self.ENTITY_SLUG,
#             user_model=self.USER_MODEL
#         )
#
#         self.LN = len(items_qs)  # evaluate the QS and cache results...
#         for form in self.forms:
#             form.fields['item_model'].queryset = items_qs
#
#
# BillItemFormset = modelformset_factory(
#     model=BillModelItemsThroughModel,
#     form=BillItemForm,
#     formset=BaseInvoiceItemFormset,
#     can_delete=True,
#     extra=5
# )
