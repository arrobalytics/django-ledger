"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CustomerModel
from django_ledger.models.customer_job import CustomerJobModel


class CreateCustomerJobModelForm(forms.ModelForm):

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
