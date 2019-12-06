from django.forms import modelformset_factory, ModelForm, HiddenInput

from django_ledger.models import AccountModel
from django_ledger.models import CoAAccountAssignments


class AccountModelForm(ModelForm):
    class Meta:
        model = AccountModel
        fields = [
            'code',
            'name',
            'role',
            'balance_type',
        ]


class CoAAssignmentsForm(ModelForm):
    class Meta:
        model = CoAAccountAssignments
        fields = '__all__'


CoAAssignmentFormSet = modelformset_factory(CoAAccountAssignments,
                                            extra=0,
                                            widgets={
                                                'coa': HiddenInput()
                                            },
                                            fields=(
                                                'coa',
                                                'account',
                                                'locked',
                                                'active'
                                            ))
