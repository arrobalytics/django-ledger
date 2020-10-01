from django.forms import (ModelForm, TextInput, BooleanField, ValidationError,
                          EmailInput, URLInput, CheckboxInput)
from django.utils.translation import gettext_lazy as _

from django_ledger.models.entity import EntityModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class EntityModelUpdateForm(ModelForm):
    class Meta:
        model = EntityModel
        fields = [
            'name',
            'address_1',
            'address_2',
            'email',
            'phone',
            'website'
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
            ),
            'address_1': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'placeholder': _('Address 1...')
                }
            ),
            'address_2': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'placeholder': _('Address 2...')
                }
            ),
            'email': EmailInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'placeholder': _('Email...')
                }
            ),
            'phone': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'placeholder': _('Phone...')
                }
            ),
            'website': URLInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'placeholder': _('Website...')
                }
            ),
        }


class EntityModelCreateForm(ModelForm):
    default_coa = BooleanField(required=True, initial=False, label=_('Populate Default CoA'))
    activate_all_accounts = BooleanField(required=True, initial=False, label=_('Activate All Accounts'))

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
            'default_coa',
            'activate_all_accounts',
            'address_1',
            'address_2',
            'email',
            'website',
            'phone'
        ]
        labels = {
            'name': _('Entity Name'),
        }
        widgets = {
            'name': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                    'placeholder': _('Entity name...'),
                    'required': True
                }
            ),
            'address_1': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Address line 1...')
            }),
            'address_2': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('City, State, ZIP...')
            }),
            'phone': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Phone number...')
            }),
            'email': EmailInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Entity email...')
            }),
            'website': URLInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Entity website...')
            }),
            'default_coa': CheckboxInput(attrs={
                'class': 'checkbox'
            })
        }
