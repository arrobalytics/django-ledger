"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.forms import ModelForm, TextInput, EmailInput, NumberInput
from django.utils.translation import gettext_lazy as _

from django_ledger.forms.utils import validate_cszc
from django_ledger.models.customer import CustomerModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class CustomerModelForm(ModelForm):

    def clean(self):
        validate_cszc(self.cleaned_data)

    class Meta:
        model = CustomerModel
        fields = [
            'customer_name',
            'address_1',
            'address_2',
            'city',
            'state',
            'zip_code',
            'country',
            'phone',
            'email',
            'website',
            'sales_tax_rate'
        ]
        help_texts = {
            'sales_tax_rate': _('Example: 3.50% should be entered as 0.0035')
        }
        widgets = {
            'customer_name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'address_1': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'address_2': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'city': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'state': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'zip_code': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'country': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            }),
            'phone': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            }),
            'email': EmailInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'website': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'sales_tax_rate': NumberInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'min': 0.000,
                'max': 1.000,
                'step': 0.001
            })
        }
