from django.forms import TextInput, Select, ModelForm

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
    Create Form: 
    This Form is used for creation of a new account that does not exist in the default Chart of Accounts. It has some external as well as some internal field.
    The entity slug and the user model are the field which are internal and are predetermined in the lass itself

    Remaining fields which needs to be defined by user are :

    code: The code will be used to uniquely identify the partiular account
    name: The name of the account. The name of the account should be resemblance of the nature of the transactions that will be in the account
    role: The role needs to be selected rom list of the options available. Choices are given under ACCOUNT ROLES. Refer the account model documentation for more info
    balance_type: Need to be selected from drop down as "Debit" or Credit"

    """
    def __init__(self, entity_slug, user_model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

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
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'role': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'balance_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }


class AccountModelCreateChildForm(AccountModelCreateForm):

    """
        
    Create Child Form: 
    This form is for creating of a child account .
    The UI is designed such that, at the time of creating the child account, we have to automatically select that particular parent
    So, we know under which parent the said Child is being created.
    
    User need to only mention the Account COde , Name and type: (Role will be same as the role of the Parent Account)

    code: The code will be used to uniquely identify the partiular account
    name: The name of the account. The name of the account should be resemblance of the nature of the transactions that will be in the account
    balance_type: Need to be selected from drop down as "Debit" or Credit"

    """

    class Meta:
        model = AccountModel
        fields = [
            'code',
            'name',
            'balance_type',
        ]
        widgets = {
            'code': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'balance_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }


class AccountModelUpdateForm(ModelForm):
    """
        
    Update Account Form: 
    This form is for updating the account. This works for both the parent or the child Account .
    
    We can update the Parent , or The Code or even the Name of the Account.
    
    """

    def __init__(self, entity_slug, user_model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.PARENT_ACCOUNT: AccountModel = self.instance.parent

        if self.PARENT_ACCOUNT:
            self.fields['parent'].queryset = AccountModel.on_coa.with_roles_available(
                entity_slug=self.ENTITY_SLUG,
                user_model=self.USER_MODEL,
                roles=[self.PARENT_ACCOUNT.role]
            )
        else:
            self.fields['parent'].queryset = AccountModel.on_coa.for_entity_available(
                user_model=self.USER_MODEL,
                entity_slug=self.ENTITY_SLUG,
            )

    class Meta:
        model = AccountModel
        fields = [
            'parent',
            'code',
            'name',
            'locked',
            'active'
        ]
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
        }
