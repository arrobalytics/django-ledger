from django.forms import ModelForm, TextInput

from django_ledger.models import LedgerModel

DJETLER_FORM_INPUT_CLASS = 'input'


class LedgerModelCreateForm(ModelForm):
    class Meta:
        model = LedgerModel
        fields = [
            'name',
        ]
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJETLER_FORM_INPUT_CLASS
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
                'class': DJETLER_FORM_INPUT_CLASS
            }),
        }
