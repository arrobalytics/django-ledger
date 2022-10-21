"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from django.forms import ModelForm, TextInput, EmailInput

from django_ledger.forms.utils import validate_cszc
from django_ledger.models.vendor import VendorModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class VendorModelForm(ModelForm):

    def clean(self):
        validate_cszc(self.cleaned_data)

    class Meta:
        model = VendorModel
        fields = [
            'vendor_name',
            'address_1',
            'address_2',
            'city',
            'state',
            'zip_code',
            'country',
            'phone',
            'email',
            'website',
            'tax_id_number'
        ]
        widgets = {
            'vendor_name': TextInput(attrs={
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
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'phone': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'email': EmailInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'website': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'tax_id_number': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }
