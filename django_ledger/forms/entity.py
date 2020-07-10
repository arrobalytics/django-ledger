from django.forms import ModelForm, TextInput, BooleanField, ValidationError
from django.utils.translation import gettext_lazy as _

from django_ledger.models.entity import EntityModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class EntityModelUpdateForm(ModelForm):
    class Meta:
        model = EntityModel
        fields = [
            'name',
        ]
        labels = {
            'name': _('Entity Name')
        }
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'placeholder': _('Entity name...')
                }
            )
        }


class EntityModelCreateForm(ModelForm):
    populate_default_coa = BooleanField(required=False, label=_('Populate Default CoA'))
    quickstart = BooleanField(required=False, label=_('Use QuickStart Data'))

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError(_('Please provide a valid name for new Entity.'))
        if len(name) < 3:
            raise ValidationError(_('Looks like this entity name is too short...'))
        return name

    class Meta:
        model = EntityModel
        fields = [
            'name',
            'populate_default_coa',
            'quickstart'
        ]
        labels = {
            'name': _('Entity Name'),
        }
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'placeholder': _('Entity name...')
                }
            )
        }
