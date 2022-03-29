"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django import forms
from django.forms import ModelForm, Select, TextInput, BaseModelFormSet, modelformset_factory, Textarea
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CustomerModel, ItemThroughModel, ItemModel
from django_ledger.models.customer_job import CustomerJobModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class CustomerJobModelCreateForm(forms.ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.fields['customer'].queryset = self.get_customer_queryset()

    def get_customer_queryset(self):
        return CustomerModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

    class Meta:
        model = CustomerJobModel
        fields = ['customer', 'title']
        widgets = {
            'customer': forms.Select(attrs={
                'id': 'djl-customer-job-title-input',
                'class': 'input'
            }),
            'title': forms.TextInput(attrs={
                'id': 'djl-customer-job-title-input',
                'class': 'input',
                'placeholder': _('Enter title...')
            })
        }


class CustomerJobModelUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomerJobModel
        fields = [
            'status',
            'markdown_notes'
        ]
        widgets = {
            'status': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'markdown_notes': Textarea(attrs={
                'class': 'textarea'
            })
        }


class CustomerJobItemForm(ModelForm):
    class Meta:
        model = ItemThroughModel
        fields = [
            'item_model',
            'entity_unit',
            'unit_cost',
            'quantity',
            'cjob_unit_revenue_estimate',
        ]
        widgets = {
            'item_model': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'entity_unit': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'unit_cost': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'cjob_unit_revenue_estimate': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'quantity': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            })
        }


class CustomerJobItemFormset(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, customer_job_model: CustomerJobModel, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.CUSTOMER_JOB_MODEL = customer_job_model
        self.ENTITY_SLUG = entity_slug

        items_qs = ItemModel.objects.for_cj(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        for form in self.forms:
            form.fields['item_model'].queryset = items_qs
            if not self.CUSTOMER_JOB_MODEL.can_edit_items():
                form.fields['item_model'].disabled = True
                form.fields['quantity'].disabled = True
                form.fields['unit_cost'].disabled = True
                form.fields['entity_unit'].disabled = True

    # def get_queryset(self):
    #     return ItemThroughModel.objects.for_cj(
    #         user_model=self.USER_MODEL,
    #         entity_slug=self.ENTITY_SLUG,
    #         cj_pk=self.CUSTOMER_JOB_MODEL.uuid
    #     )

# todo: add instance where can_delete = False
CustomerJobItemFormset = modelformset_factory(
    model=ItemThroughModel,
    form=CustomerJobItemForm,
    formset=CustomerJobItemFormset,
    can_delete=True,
    extra=5
)
