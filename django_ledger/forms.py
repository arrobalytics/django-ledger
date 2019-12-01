from django import forms

from django_ledger.models import AccountModel


class AccountModelForm(forms.ModelForm):
    class Meta:
        model = AccountModel
        fields = [
            'code',
            'name',
            'role',
            'balance_type',
            'locked'
        ]
