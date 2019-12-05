from django import forms
from django.forms import modelformset_factory

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


CoAAssignmentFormSet = modelformset_factory(CoAAccountAssignments,
                                            extra=2,
                                            fields=(
                                                'account',
                                                'locked',
                                                'active'
                                            ))
