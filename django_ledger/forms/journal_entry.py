from typing import Union
from uuid import UUID

from django.forms import ModelForm, Textarea, Select, DateTimeInput, ValidationError
from django.utils.translation import gettext_lazy as _

from django_ledger.models import EntityModel
from django_ledger.models.journal_entry import JournalEntryModel
from django_ledger.models.ledger import LedgerModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class JournalEntryModelCreateForm(ModelForm):
    def __init__(self,
                 entity_model: EntityModel,
                 ledger_model: Union[str, UUID, LedgerModel],
                 *args, **kwargs
                 ):
        super().__init__(*args, **kwargs)
        self.ENTITY_MODEL: EntityModel = entity_model

        # processes the provided ledger model UUID is valid....
        if isinstance(ledger_model, (str, UUID)):
            ledger_model = self.ENTITY_MODEL.get_ledgers().get(uuid__exact=ledger_model)
        elif isinstance(ledger_model, LedgerModel):
            self.ENTITY_MODEL.validate_ledger_model_for_entity(ledger_model)

        self.LEDGER_MODEL: LedgerModel = ledger_model

        if 'timestamp' in self.fields:
            self.fields['timestamp'].required = False
        if 'entity_unit' in self.fields:
            self.fields['entity_unit'].queryset = self.ENTITY_MODEL.entityunitmodel_set.all()

    def clean(self):
        if self.LEDGER_MODEL.is_locked():
            raise ValidationError(message=_('Cannot create new Journal Entries on a locked Ledger.'))
        self.instance.ledger = self.LEDGER_MODEL
        return super().clean()

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
                'type': 'datetime-local',
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'description': Textarea(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            })
        }
        labels = {
            'entity_unit': _('Entity Unit')
        }


class JournalEntryModelUpdateForm(ModelForm):

    def clean_timestamp(self):
        if 'timestamp' in self.changed_data:
            new_timestamp = self.cleaned_data['timestamp']
            je_model: JournalEntryModel = self.instance
            if je_model.is_in_locked_period(new_timestamp=new_timestamp):
                raise ValidationError(
                    message=_(f'Invalid timestamp {self.cleaned_data["timestamp"]} due to Closing Entries.')
                )
        return self.cleaned_data['timestamp']

    class Meta(JournalEntryModelCreateForm.Meta):
        model = JournalEntryModel
        fields = [
            'timestamp',
            'entity_unit',
            'description'
        ]


class JournalEntryModelCannotEditForm(JournalEntryModelUpdateForm):
    class Meta(JournalEntryModelCreateForm.Meta):
        fields = [
            'description'
        ]
