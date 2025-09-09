from django.forms import DateInput, ValidationError, ModelForm, Textarea, HiddenInput
from django.utils.translation import gettext_lazy as _

from django_ledger.io.io_core import get_localdate
from django_ledger.models.closing_entry import ClosingEntryModel
from django_ledger.models.entity import EntityModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class ClosingEntryCreateForm(ModelForm):

    def __init__(self, entity_model: EntityModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_MODEL: EntityModel = entity_model
        self.fields['entity_model'].disabled = True

    def clean_entity_model(self):
        return self.ENTITY_MODEL

    def clean_closing_date(self):
        closing_date = self.cleaned_data['closing_date']

        if closing_date > get_localdate():
            raise ValidationError(
                message=_('Cannot create a closing entry with a future date.'), code='invalid_date'
            )
        return closing_date

    class Meta:
        model = ClosingEntryModel
        fields = [
            'entity_model',
            'closing_date'
        ]

        widgets = {
            'entity_model': HiddenInput(),
            'closing_date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                'placeholder': _('Closing Date (YYYY-MM-DD)...'),
                'id': 'djl-datepicker',
                'type': 'date'
            })
        }
        labels = {
            'closing_date': _('Select a Closing Date')
        }


class ClosingEntryUpdateForm(ModelForm):
    class Meta:
        model = ClosingEntryModel
        fields = [
            'markdown_notes'
        ]

        widgets = {
            'markdown_notes': Textarea(attrs={
                'class': 'textarea'
            }),
        }
        labels = {
            'markdown_notes': _('Closing Entry Notes')
        }
