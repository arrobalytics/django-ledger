from django.forms import ModelForm, TextInput, Textarea
from django.utils.translation import gettext_lazy as _

from django_ledger.models.coa import ChartOfAccountModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class ChartOfAccountsModelForm(ModelForm):
    class Meta:
        model = ChartOfAccountModel
        fields = [
            'name',
            'description'
        ]
        labels = {
            'name': _('Name'),
            'description': _('Description'),
        }
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'description': Textarea(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }


class ChartOfAccountsModelUpdateForm(ModelForm):
    class Meta:
        model = ChartOfAccountModel
        fields = [
            'name',
            'active'
        ]
        labels = {
            'name': _('Name'),
            'description': _('Description'),
        }
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'description': Textarea(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }
