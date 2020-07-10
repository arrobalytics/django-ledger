from django.forms import ModelForm, TextInput, Select

from django_ledger.models.accounts import AccountModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class AccountModelBaseForm(ModelForm):

    def __init__(self, coa_slug, entity_slug, user_model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.COA_SLUG = coa_slug
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        account_qs = AccountModel.on_coa.for_entity_available(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG,
            coa_slug=self.COA_SLUG
        )
        self.fields['parent'].queryset = account_qs


class AccountModelCreateForm(AccountModelBaseForm):
    class Meta:
        model = AccountModel
        fields = [
            'parent',
            'code',
            'name',
            'role',
            'balance_type',
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
            'role': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'balance_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),

        }


class AccountModelUpdateForm(AccountModelBaseForm):
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
