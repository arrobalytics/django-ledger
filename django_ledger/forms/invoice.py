from django.forms import ModelForm

from django_ledger.models import InvoiceModel


class InvoiceModelForm(ModelForm):
    class Meta:
        model = InvoiceModel
        fields = '__all__'
