from typing import Optional

from django.forms import TextInput, Select, ModelForm, ChoiceField
from django.utils.translation import gettext_lazy as _
from treebeard.forms import MoveNodeForm

from django_ledger.io import ACCOUNT_CHOICES_NO_ROOT
from django_ledger.models.accounts import AccountModel, AccountModelQuerySet
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES

"""
The account Model has the below forms: All these form have Account Model as their base.

CreateForm
CreateChildForm
Update Form
"""


class AccountModelCreateForm(ModelForm):
    """
    Create Form: 
    This Form is used for creation of a new account that does not exist in the default Chart of Accounts. It has some external as well as some internal field.
    The entity slug and the user model are the field which are internal and are predetermined in the lass itself

    Remaining fields which needs to be defined by user are :

    code: The code will be used to uniquely identify the particular account
    name: The name of the account. The name of the account should be resemblance of the nature of the transactions that will be in the account
    role: The role needs to be selected rom list of the options available. Choices are given under ACCOUNT ROLES. Refer the account model documentation for more info
    balance_type: Need to be selected from drop down as "Debit" or Credit"
    """

    def __init__(self, entity_slug, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = ACCOUNT_CHOICES_NO_ROOT
        self.fields['code'].required = False

    class Meta:
        model = AccountModel
        fields = [
            'code',
            'name',
            'role',
            'balance_type',
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
            'balance_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }


class AccountModelUpdateForm(MoveNodeForm):
    """
    Update Account Form:
    This form is for updating the account. This works for both the parent or the child Account .
    We can update the Parent , or The Code or even the Name of the Account.
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

    def __init__(self, entity_slug, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)
        # self.fields['_ref_node_id'].choices = self.mk_dropdown_tree_choices()

    @classmethod
    def mk_dropdown_tree(cls, model, for_node: Optional[AccountModel] = None):
        """ Creates a tree-like list of choices """

        options = [(None, _('-- root --'))]
        qs: AccountModelQuerySet = model.get_root_nodes()

        if for_node:
            qs = qs.for_entity(
                entity_slug=for_node.coa_model.entity.slug,
                # must be set on view...
                user_model=getattr(for_node, 'USER_MODEL')
            ).with_roles(roles=for_node.role).active()

        for node in qs:
            cls.add_subtree(for_node, node, options)
        return options

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
            })
        }
