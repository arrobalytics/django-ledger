"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
"""

from random import randint

from django.forms import (
    TextInput,
    Select,
    ModelForm,
    ChoiceField,
    ModelChoiceField,
    CheckboxInput,
    HiddenInput,
)
from django.utils.translation import gettext_lazy as _
from treebeard.forms import MoveNodeForm

from django_ledger.io import ACCOUNT_CHOICES_NO_ROOT
from django_ledger.models import ChartOfAccountModel, AccountModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES

FORM_META_FIELDS = [
    'code',
    'name',
    'role',
    'role_default',
    'balance_type',
    'active',
    'coa_model',
]
FORM_META_WIDGETS = {
    'code': TextInput(
        attrs={
            'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            'placeholder': _('Alpha Numeric (auto generated if not provided)...'),
        }
    ),
    'name': TextInput(
        attrs={
            'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            'placeholder': _('Account Name...'),
        }
    ),
    'role': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
    'role_default': CheckboxInput(),
    'balance_type': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
    'coa_model': HiddenInput(),
    'parent': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
    'position': HiddenInput()
}
class AccountModelCreateForm(ModelForm):
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

    def clean_coa_model(self):
        return self.COA_MODEL

    class Meta:
        model = AccountModel
        fields = FORM_META_FIELDS
        widgets = FORM_META_WIDGETS


class AccountModelUpdateForm(MoveNodeForm):
    # treebeard >= 7 names the move fields treebeard_position / treebeard_ref_node.
    treebeard_position = ChoiceField(
        required=True,
        label=_('Position'),
        widget=HiddenInput(),
    )
    treebeard_ref_node = ModelChoiceField(
        required=True,
        label=_('Parent Account'),
        queryset=AccountModel.objects.none(),
        empty_label=_('-- Select parent --'),
        widget=Select(),
    )

    field_order = [
        'code',
        'name',
        'role',
        'balance_type',
        'role_default',
        'treebeard_ref_node',
        'treebeard_position',
        'active',
        'coa_model',
    ]

    POSITION_CHOICES = [
        ('first-child', _('First child')),
        ('last-child', _('Last child')),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].disabled = True
        self.fields['coa_model'].disabled = True
        for name in ('role', 'balance_type'):
            self.fields[name].widget.attrs['class'] = ''
        position_field = self.fields['treebeard_position']
        position_field.choices = self.POSITION_CHOICES
        # self.initial (set by MoveNodeForm) takes precedence over field.initial.
        self.initial['treebeard_position'] = 'last-child'
        ref_node_field = self.fields['treebeard_ref_node']
        ref_node_field.label_from_instance = lambda obj: f'{"-" * (obj.depth - 1)} {obj.code} - {obj.name}'
        if self.instance and self.instance.pk:
            ref_node_field.queryset = self.instance.get_account_move_choice_queryset()
            parent = self.instance.get_parent()
            self.initial['treebeard_ref_node'] = parent.pk if parent else None

    def clean_role(self):
        return self.instance.role

    def clean_coa_model(self):
        return self.instance.coa_model

    class Meta:
        model = AccountModel
        exclude = ('depth', 'numchild', 'path')
        widgets = FORM_META_WIDGETS
