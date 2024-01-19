from django.core.exceptions import ValidationError
from django.forms import ModelForm, TextInput, Select
from django.utils.translation import gettext_lazy as _

from django_ledger.models.ledger import LedgerModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class LedgerModelCreateForm(ModelForm):

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG: str = entity_slug
        self.USER_MODEL = user_model

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('entity')
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            self._update_errors(e)

    class Meta:
        model = LedgerModel
        fields = [
            'name',
            'ledger_xid'
        ]
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                }
            ),
            'ledger_xid': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                }
            ),
        }
        labels = {
            'ledger_xid': _('Ledger External ID')
        }


class LedgerModelUpdateForm(LedgerModelCreateForm):
    class Meta:
        model = LedgerModel
        fields = [
            'name',
            'hidden'
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'entity_unit': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }
