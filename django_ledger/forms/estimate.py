"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django import forms
from django.forms import ModelForm, Select, TextInput, BaseModelFormSet, modelformset_factory, Textarea, ValidationError
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CustomerModel, ItemThroughModel, ItemModel, EntityUnitModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class CustomerEstimateCreateForm(forms.ModelForm):

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
        model = EstimateModel
        fields = ['customer', 'title', 'terms']
        widgets = {
            'customer': forms.Select(attrs={
                'id': 'djl-customer-estimate-customer-input',
                'class': 'input'
            }),
            'terms': forms.Select(attrs={
                'id': 'djl-customer-estimate-terms-input',
                'class': 'input'
            }),
            'title': forms.TextInput(attrs={
                'id': 'djl-customer-job-title-input',
                'class': 'input',
                'placeholder': _('Enter title...')
            })
        }


class CustomerEstimateModelUpdateForm(forms.ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.ENTITY_SLUG = entity_slug
        self.CUSTOMER_ESTIMATE_MODEL: EstimateModel = self.instance

        if not self.CUSTOMER_ESTIMATE_MODEL.can_update_terms():
            self.fields['terms'].disabled = True

    def clean(self):
        cleaned_data = super(CustomerEstimateModelUpdateForm, self).clean()
        if 'status' in self.changed_data:
            ce_model: EstimateModel = self.instance
            new_status = cleaned_data['status']
            ce_model.can_change_status(new_status=new_status)
        return cleaned_data

    class Meta:
        model = EstimateModel
        fields = [
            'terms',
            'markdown_notes'
        ]
        widgets = {
            'terms': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'markdown_notes': Textarea(attrs={
                'class': 'textarea'
            })
        }


class CustomerEstimateItemForm(ModelForm):
    class Meta:
        model = ItemThroughModel
        fields = [
            'item_model',
            'entity_unit',
            'unit_cost',
            'quantity',
            'ce_unit_revenue_estimate',
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
            'ce_unit_revenue_estimate': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'quantity': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            })
        }


class BaseCustomerEstimateItemFormset(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, customer_job_model: EstimateModel, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.CUSTOMER_JOB_MODEL = customer_job_model
        self.ENTITY_SLUG = entity_slug

        items_qs = ItemModel.objects.for_cj(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        unit_qs = EntityUnitModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        for form in self.forms:
            form.fields['item_model'].queryset = items_qs
            form.fields['entity_unit'].queryset = unit_qs

            if not self.CUSTOMER_JOB_MODEL.can_update_items():
                form.fields['item_model'].disabled = True
                form.fields['quantity'].disabled = True
                form.fields['unit_cost'].disabled = True
                form.fields['entity_unit'].disabled = True
                form.fields['ce_unit_revenue_estimate'].disabled = True


# todo: add instance where can_delete = False
CustomerEstimateItemFormset = modelformset_factory(
    model=ItemThroughModel,
    form=CustomerEstimateItemForm,
    formset=BaseCustomerEstimateItemFormset,
    can_delete=True,
    extra=5
)

CustomerEstimateItemFormsetReadOnly = modelformset_factory(
    model=ItemThroughModel,
    form=CustomerEstimateItemForm,
    formset=BaseCustomerEstimateItemFormset,
    can_delete=False,
    extra=0
)
