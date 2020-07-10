from django.forms import ModelForm, TextInput

from django_ledger.models.ledger import LedgerModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class LedgerModelCreateForm(ModelForm):
    class Meta:
        model = LedgerModel
        fields = [
            'name',
        ]
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                }
            ),
        }


class LedgerModelUpdateForm(ModelForm):
    class Meta:
        model = LedgerModel
        fields = [
            'name',
            'posted',
            'locked',
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }
