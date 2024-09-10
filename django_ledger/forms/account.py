from typing import Optional

from django.forms import TextInput, Select, ModelForm, ChoiceField, ValidationError, CheckboxInput
from django.utils.translation import gettext_lazy as _
from treebeard.forms import MoveNodeForm

from django_ledger.io import ACCOUNT_CHOICES_NO_ROOT
from django_ledger.models.accounts import AccountModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES

"""
The account Model has the below forms: All these form have Account Model as their base.

CreateForm
CreateChildForm
Update Form
"""


class AccountModelCreateForm(ModelForm):
    """
    AccountModelCreateForm
    ======================

    A form for creating and managing account models within the system.

    Attributes
    ----------
    ENTITY : Model
        The entity model being used in the form.
    COA_MODEL : Model
        The Chart of Account Model being used in the form.
    USER_MODEL : Model
        The user model being used in the form.

    """

    def __init__(self, entity_model, coa_model, user_model, *args, **kwargs):
        self.ENTITY = entity_model
        self.COA_MODEL = coa_model
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = ACCOUNT_CHOICES_NO_ROOT
        self.fields['code'].required = False

    def clean_role_default(self):
        role_default = self.cleaned_data['role_default']
        if not role_default:
            return None
        return role_default

    def clean_code(self):
        code = self.cleaned_data['code']
        is_code_valid = not self.COA_MODEL.accountmodel_set.filter(code=code).exists()
        if not is_code_valid:
            raise ValidationError(message=_('Code {} already exists for CoA {}').format(code, self.COA_MODEL.slug))
        return code

    class Meta:
        model = AccountModel
        fields = [
            'code',
            'name',
            'role',
            'role_default',
            'balance_type',
            'active',
            'active'
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
                            label=_("Position"),
                            widget=Select(attrs={
                                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                            }))
    _ref_node_id = ChoiceField(required=False,
                               label=_("Relative to"),
                               widget=Select(attrs={
                                   'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                               }))

    def __init__(self, entity_model, coa_model, user_model, *args, **kwargs):
        self.ENTITY = entity_model
        self.COA_MODEL = coa_model
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)
        # self.fields['_ref_node_id'].choices = self.mk_dropdown_tree_choices()

    @classmethod
    def mk_dropdown_tree(cls, model, for_node: Optional[AccountModel] = None):
        """ Creates a tree-like list of choices """

        if not for_node:
            raise ValidationError(message='Must provide for_node argument.')

        options = list()
        qs = for_node.get_account_move_choice_queryset()

        # for node in qs:
        #     cls.add_subtree(for_node, node, options)
        return [
            (i.uuid, f'{"-" * (i.depth - 1)} {i}') for i in qs
        ]

    def clean_role_default(self):
        role_default = self.cleaned_data['role_default']
        if not role_default:
            return None
        return role_default

    class Meta:
        model = AccountModel
        exclude = ('depth', 'numchild', 'path', 'balance_type', 'role')
        widgets = {
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
