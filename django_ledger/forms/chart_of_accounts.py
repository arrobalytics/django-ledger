from random import randint

from django.forms import ModelForm, TextInput, Textarea, HiddenInput
from django.utils.translation import gettext_lazy as _

from django_ledger.models.chart_of_accounts import ChartOfAccountModel
from django_ledger.models.entity import EntityModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class ChartOfAccountsModelCreateForm(ModelForm):
    FORM_ID_SEP = '___'

    def __init__(self, entity_model: EntityModel, *args, **kwargs):
        self.ENTITY_MODEL = entity_model
        super().__init__(*args, **kwargs)
        self.fields['entity'].disabled = True
        self.fields['entity'].required = True
        self.form_id: str = self.get_form_id()

    def clean_entity(self):
        return self.ENTITY_MODEL

    def get_form_id(self) -> str:
        return f'coa-model-create-form-{self.ENTITY_MODEL.slug}{self.FORM_ID_SEP}{randint(100000, 999999)}'

    class Meta:
        model = ChartOfAccountModel
        fields = [
            'entity',
            'name',
            'description'
        ]
        labels = {
            'name': _('Name'),
            'description': _('Description'),
        }
        widgets = {
            'entity': HiddenInput(),
            'name': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                }),
            'description': Textarea(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                }
            ),
        }


class ChartOfAccountsModelUpdateForm(ModelForm):

    FORM_ID_SEP = '___'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_id: str = self.get_form_id()


    def get_form_id(self) -> str:
        instance: ChartOfAccountModel = self.instance
        return f'coa-model-update-form-{instance.slug}{self.FORM_ID_SEP}{randint(100000, 999999)}'

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
