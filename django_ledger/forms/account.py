"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""
from random import randint
from typing import Optional

from django.forms import TextInput, Select, ModelForm, ChoiceField, ValidationError, CheckboxInput, HiddenInput
from django.utils.translation import gettext_lazy as _
from treebeard.forms import MoveNodeForm

from django_ledger.io import ACCOUNT_CHOICES_NO_ROOT
from django_ledger.models import ChartOfAccountModel, EntityModel
from django_ledger.models.accounts import AccountModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class AccountModelCreateForm(ModelForm):
    """
    A form for creating and managing account models within the system.

    Attributes
    ----------
    ENTITY_MODEL : Model
        The entity model being used in the form.
    COA_MODEL : Model
        The Chart of Account Model being used in the form.
    """

    FORM_ID_SEP = '___'

    def __init__(self, coa_model: ChartOfAccountModel, *args, **kwargs):
        self.COA_MODEL: ChartOfAccountModel = coa_model
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = ACCOUNT_CHOICES_NO_ROOT
        self.fields['code'].required = False
        self.fields['coa_model'].disabled = True
        self.fields['coa_model'].required = True

        self.form_id: str = self.get_form_id()

    def get_form_id(self) -> str:
        return f'account-model-create-form-{self.COA_MODEL.slug}{self.FORM_ID_SEP}{randint(100000, 999999)}'

    def clean_role_default(self):
        role_default = self.cleaned_data['role_default']
        if not role_default:
            return None
        return role_default

    def clean_coa_model(self):
        return self.COA_MODEL

    class Meta:
        model = AccountModel
        fields = [
            'code',
            'name',
            'role',
            'role_default',
            'balance_type',
            'active',
            'active',
            'coa_model'
        ]
        widgets = {
            'code': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Alpha Numeric (auto generated if not provided)...')
            }),
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Account Name...')
            }),
            'role': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'role_default': CheckboxInput(),
            'balance_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'coa_model': HiddenInput()
        }


class AccountModelUpdateForm(MoveNodeForm):
    """
    AccountModelUpdateForm

    A form for updating account model, inheriting from MoveNodeForm.

    Attributes
    ----------
    _position : ChoiceField
        A choice field for selecting the position.
    _ref_node_id : ChoiceField
        An optional choice field for selecting the relative node.
    """

    _position = ChoiceField(required=True,
                            label=_('Position'),
                            widget=Select(attrs={
                                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                            }))
    _ref_node_id = ChoiceField(required=False,
                               label=_('Relative to'),
                               widget=Select(attrs={
                                   'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                               }))


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].disabled = True
        self.fields['coa_model'].disabled = True


    @classmethod
    def mk_dropdown_tree(cls, model, for_node: Optional[AccountModel] = None):
        """ Creates a tree-like list of choices """

        if not for_node:
            raise ValidationError(message='Must provide for_node argument.')

        qs = for_node.get_account_move_choice_queryset()

        return [
            (i.uuid, f'{"-" * (i.depth - 1)} {i}') for i in qs
        ]

    def clean_role(self):
        return self.instance.role

    def coa_model(self):
        return self.instance.coa_model

    def clean_role_default(self):
        role_default = self.cleaned_data['role_default']
        if not role_default:
            return None
        return role_default

    class Meta:
        model = AccountModel
        exclude = ('depth', 'numchild', 'path', 'balance_type')
        widgets = {
            'role': HiddenInput(),
            'coa_model': HiddenInput(),
            'parent': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'code': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'role_default': CheckboxInput(),
        }
