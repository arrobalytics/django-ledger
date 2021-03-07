from django.forms import ModelForm, TextInput, Select

from django_ledger.models.ledger import LedgerModel
from django_ledger.models.unit import EntityUnitModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class LedgerModelCreateForm(ModelForm):

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG: str = entity_slug
        self.USER_MODEL = user_model
        self.fields['entity_unit'].queryset = EntityUnitModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

    class Meta:
        model = LedgerModel
        fields = [
            'name',
            # 'unit'
        ]
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                }
            ),
            'entity_unit': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }


class LedgerModelUpdateForm(LedgerModelCreateForm):
    class Meta:
        model = LedgerModel
        fields = [
            'name',
            # 'unit',
            'posted',
            'locked',
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'entity_unit': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }
