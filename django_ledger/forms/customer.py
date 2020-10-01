from django.forms import ModelForm, TextInput, EmailInput

from django_ledger.models.customer import CustomerModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class CustomerModelForm(ModelForm):
    class Meta:
        model = CustomerModel
        fields = [
            'customer_name',
            'address_1',
            'address_2',
            'phone',
            'email',
            'website',
        ]
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
            'phone': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'email': EmailInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'website': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }
