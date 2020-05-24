from django.forms import (ModelForm, modelformset_factory, BaseModelFormSet, TextInput, Textarea, BooleanField, Select,
                          DateInput, ValidationError)
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l

from django_ledger.io import validate_tx_data
from django_ledger.models import (AccountModel, LedgerModel, JournalEntryModel, TransactionModel,
                                  ChartOfAccountModel, EntityModel)

# todo: move this to settings & make it a list...
DJETLER_FORM_INPUT_CLASS = 'input'


class EntityModelUpdateForm(ModelForm):
    class Meta:
        model = EntityModel
        fields = [
            'name',
        ]
        labels = {
            'name': _l('Entity Name')
        }
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJETLER_FORM_INPUT_CLASS,
                    'placeholder': _l('Entity name...')
                }
            )
        }


class EntityModelCreateForm(ModelForm):
    populate_default_coa = BooleanField(required=False, label=_l('Populate Default CoA'))
    quickstart = BooleanField(required=False, label=_l('Use QuickStart Data'))

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
            'name': _l('Entity Name'),
        }
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJETLER_FORM_INPUT_CLASS,
                    'placeholder': _l('Entity name...')
                }
            )
        }


class ChartOfAccountsModelForm(ModelForm):
    class Meta:
        model = ChartOfAccountModel
        fields = [
            'slug',
            'name',
            'description'
        ]
        labels = {
            'slug': _l('CoA ID'),
            'name': _l('Name'),
            'description': _l('Description'),
        }
        widgets = {
            'slug': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'name': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'description': Textarea(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
        }


class ChartOfAccountsModelUpdateForm(ModelForm):
    class Meta:
        model = ChartOfAccountModel
        fields = [
            'name',
            'locked'
        ]
        labels = {
            'name': _l('Name'),
            'description': _l('Description'),
        }
        widgets = {
            'name': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
            'description': Textarea(attrs={
                'class': DJETLER_FORM_INPUT_CLASS
            }),
        }


