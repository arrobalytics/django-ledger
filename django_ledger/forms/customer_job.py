from django import forms
from django.utils.translation import gettext_lazy as _

from django_ledger.models.customer_job import CustomerJobModel


class CreateCustomerJobModelForm(forms.ModelForm):
    class Meta:
        model = CustomerJobModel
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'id': 'djl-customer-job-title-input',
                'class':'input',
                'placeholder': _('Enter title...')
            })
        }