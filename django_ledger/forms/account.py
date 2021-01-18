from django.forms import TextInput, Select, ModelForm

from django_ledger.models.accounts import AccountModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class AccountModelCreateForm(ModelForm):
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
