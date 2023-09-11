from django.forms import ModelForm, Textarea, Select, DateTimeInput
from django.utils.translation import gettext_lazy as _

from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.unit import EntityUnitModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class JournalEntryModelCreateForm(ModelForm):
    def __init__(self, entity_slug: str, ledger_pk: str, user_model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.LEDGER_PK = ledger_pk
        self.fields['timestamp'].required = False

        if 'entity_unit' in self.fields:
            self.fields['entity_unit'].queryset = EntityUnitModel.objects.for_entity(
                entity_slug=self.ENTITY_SLUG,
                user_model=self.USER_MODEL
            )

    class Meta:
        model = JournalEntryModel
        fields = [
            'timestamp',
            'entity_unit',
            'description'
        ]
        widgets = {
            'parent': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'entity_unit': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'timestamp': DateTimeInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'description': Textarea(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            })
        }
        labels = {
            'entity_unit': _('Entity Unit')
        }


class JournalEntryModelUpdateForm(JournalEntryModelCreateForm):
    class Meta(JournalEntryModelCreateForm.Meta):
        fields = [
            'timestamp',
            'description'
        ]
