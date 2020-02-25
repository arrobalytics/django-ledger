from django.forms import ModelForm, DateInput, TextInput, Select, EmailInput, URLInput
from django.forms import ValidationError

from django_ledger.forms import DJETLER_FORM_INPUT_CLASS
from django_ledger.models import InvoiceModel


class InvoiceModelCreateForm(ModelForm):
    class Meta:
        model = InvoiceModel
        fields = [
            'date',
            'amount_due',
            'terms',
            'bill_to',
            'address_1',
            'address_2',
            'phone',
            'email',
            'website',
            'cash_account',
            'receivable_account',
            'payable_account',
            'income_account'
        ]
        widgets = {
            'date': DateInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'amount_due': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'terms': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'bill_to': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'address_1': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'address_2': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'phone': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'email': EmailInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'website': URLInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'cash_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'receivable_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'payable_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'income_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
        }


class InvoiceModelUpdateForm(ModelForm):

    def clean(self):
        amount_paid = self.cleaned_data.get('amount_paid')
        amount_due = self.cleaned_data.get('amount_due')
        if amount_paid > amount_due:
            raise ValidationError(
                'Amount paid cannot exceed invoice amount due'
            )

    class Meta:
        model = InvoiceModel
        fields = [
            'bill_to',
            'address_1',
            'address_2',
            'phone',
            'email',
            'website',
            'date',
            'terms',
            'amount_due',
            'amount_paid',
            'paid',
            'paid_date',
            'progress',
            'progressible'
        ]
        widgets = {
            'bill_to': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'address_1': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'address_2': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'phone': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'email': EmailInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'website': URLInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),

            'date': DateInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'paid_date': DateInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'amount_due': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'amount_paid': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'terms': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),

            'progress': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),

            'cash_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'receivable_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'payable_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'income_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
        }
