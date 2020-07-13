from django.forms import ModelForm, Textarea, Select, DateInput

from django_ledger.models.journalentry import JournalEntryModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class JournalEntryModelCreateForm(ModelForm):
    def __init__(self, entity_slug: str, ledger_pk: str, user_model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.LEDGER_PK = ledger_pk

        self.fields['parent'].queryset = JournalEntryModel.on_coa.for_ledger(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL,
            ledger_pk=self.LEDGER_PK
        )

    class Meta:
        model = JournalEntryModel
        fields = [
            'parent',
            'activity',
            'date',
            'description'
        ]
        widgets = {
            'parent': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'activity': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'description': Textarea(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            })
        }


class JournalEntryModelUpdateForm(JournalEntryModelCreateForm):
    class Meta:
        model = JournalEntryModel
        fields = [
            'parent',
            'activity',
            'date',
            'description',
            'locked',
            'posted'
        ]
        widgets = {
            'parent': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'activity': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'description': Textarea(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            })
        }
