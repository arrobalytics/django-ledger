"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django import forms
from django.forms import ModelForm, Select, TextInput, BaseModelFormSet, modelformset_factory, Textarea, ValidationError
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CustomerModel, ItemTransactionModel, ItemModel, EntityUnitModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class EstimateModelCreateForm(forms.ModelForm):

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
        fields = ['title', 'customer', 'terms']
        widgets = {
            'customer': forms.Select(attrs={
                'id': 'djl-customer-estimate-customer-input',
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'terms': forms.Select(attrs={
                'id': 'djl-customer-estimate-terms-input',
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'title': forms.TextInput(attrs={
                'id': 'djl-customer-job-title-input',
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                'placeholder': _('Estimate title...')
            })
        }


class BaseEstimateModelUpdateForm(forms.ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.ENTITY_SLUG = entity_slug
        self.CUSTOMER_ESTIMATE_MODEL: EstimateModel = self.instance

    class Meta:
        model = EstimateModel
        fields = [
            'markdown_notes'
        ]
        widgets = {
            'terms': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'markdown_notes': Textarea(attrs={
                'class': 'textarea'
            })
        }


class DraftEstimateModelUpdateForm(BaseEstimateModelUpdateForm):
    class Meta(BaseEstimateModelUpdateForm.Meta):
        fields = [
            'terms',
            'markdown_notes'
        ]


class EstimateItemModelForm(ModelForm):
    class Meta:
        model = ItemTransactionModel
        fields = [
            'item_model',
            'entity_unit',
            'ce_quantity',
            'ce_unit_cost_estimate',
            'ce_unit_revenue_estimate',
        ]
        widgets = {
            'item_model': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'entity_unit': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'ce_unit_cost_estimate': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'ce_unit_revenue_estimate': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'ce_quantity': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            })
        }


class BaseEstimateItemModelFormset(BaseModelFormSet):

    def __init__(self, *args, entity_slug, user_model, customer_job_model: EstimateModel, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.ESTIMATE_MODEL = customer_job_model
        self.ENTITY_SLUG = entity_slug

        items_qs = ItemModel.objects.for_estimate(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        unit_qs = EntityUnitModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        # todo: use different forms instead...
        for form in self.forms:
            form.fields['item_model'].queryset = items_qs
            form.fields['entity_unit'].queryset = unit_qs

            if not self.ESTIMATE_MODEL.can_update_items():
                form.fields['item_model'].disabled = True
                form.fields['ce_unit_cost_estimate'].disabled = True
                form.fields['ce_quantity'].disabled = True
                form.fields['ce_unit_revenue_estimate'].disabled = True
                form.fields['entity_unit'].disabled = True


# todo: add instance where can_delete = False
CanEditEstimateItemModelFormset = modelformset_factory(
    model=ItemTransactionModel,
    form=EstimateItemModelForm,
    formset=BaseEstimateItemModelFormset,
    can_delete=True,
    extra=5
)

ReadOnlyEstimateItemModelFormset = modelformset_factory(
    model=ItemTransactionModel,
    form=EstimateItemModelForm,
    formset=BaseEstimateItemModelFormset,
    can_delete=False,
    extra=0
)
