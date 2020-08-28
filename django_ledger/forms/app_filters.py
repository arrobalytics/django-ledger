from django.forms import Form, ModelChoiceField, Select, ChoiceField, CharField, HiddenInput, DateField, DateInput
from django.utils.translation import gettext_lazy as _l

from django_ledger.models.entity import EntityModel
from django_ledger.models.journalentry import ACTIVITIES
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class EntityFilterForm(Form):
    entity_model = ModelChoiceField(
        queryset=EntityModel.objects.none(),
        widget=Select(attrs={
            'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' djetler-set-entity-form-input',
        }))

    def __init__(self, *args, user_model, default_entity=None, form_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.form_id = form_id
        self.fields['entity_model'].queryset = EntityModel.objects.for_user(
            user_model=self.USER_MODEL).only('slug', 'name')
        if form_id:
            self.fields['entity_model'].widget.attrs['class'] += f' djetler-default-entity-input-{self.form_id}'
        if default_entity:
            self.initial = {
                'entity_model': default_entity
            }


class ActivityFilterForm(Form):
    CHOICES = [('all', _l('All'))] + ACTIVITIES
    activity = ChoiceField(choices=CHOICES,
                           label=_l('Activity'),
                           initial='all',
                           widget=Select(
                               attrs={
                                   'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small djetler-activity-select-form-input',
                               }
                           ))


class AsOfDateFilterForm(Form):

    def __init__(self, *args, form_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_id = form_id
        if form_id:
            self.fields['date'].widget.attrs['class'] += f' djetler-end-date-filter-input-{self.form_id}'

    entity_slug = CharField(
        max_length=150,
        widget=HiddenInput()
    )
    date = DateField(
        widget=DateInput(
            attrs={
                'class': 'is-hidden',
                'data-input': True,
            }
        ))
