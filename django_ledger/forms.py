from django import forms

from django_ledger.models import AccountModel
from django_ledger.models import CoAAccountAssignments


class AccountModelForm(forms.ModelForm):
    class Meta:
        model = AccountModel
        fields = [
            'code',
            'name',
            'role',
            'balance_type',
        ]


class CoAAssignmentsForm(forms.ModelForm):
    class Meta:
        model = CoAAccountAssignments
        fields = '__all__'
