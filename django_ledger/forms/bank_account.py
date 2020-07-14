from django.forms import ModelForm, TextInput, Select
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import ASSET_CA_CASH
from django_ledger.models import BankAccountModel
from django_ledger.models.accounts import AccountModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class BankAccountCreateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        account_qs = AccountModel.on_coa.for_entity_available(user_model=self.USER_MODEL,
                                                              entity_slug=self.ENTITY_SLUG)
        self.fields['cash_account'].queryset = account_qs.filter(role__exact=ASSET_CA_CASH)

    class Meta:
        model = BankAccountModel
        fields = [
            'name',
            'account_type',
            'account_number',
            'routing_number',
            'aba_number',
            'cash_account',
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Enter account name...')
            }),
            'account_number': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Enter account number...')
            }),
            'routing_number': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Enter routing number...')
            }),
            'aba_number': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Enter ABA number...')
            }),
            'account_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'cash_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            })
        }
        labels = {
            'name': _('Account Name'),
            'account_number': _('Account Number'),
            'account_type': _('Account Type'),
            'cash_account': _('Cash Account'),
            'aba_number': _('ABA Number'),
            'routing_number': _('Routing Number'),
        }


class BankAccountUpdateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

        account_qs = AccountModel.on_coa.for_entity_available(user_model=self.USER_MODEL,
                                                              entity_slug=self.ENTITY_SLUG)
        self.fields['cash_account'].queryset = account_qs.filter(role__exact=ASSET_CA_CASH)

    class Meta:
        model = BankAccountModel
        fields = [
            'name',
            'account_type',
            'account_number',
            'routing_number',
            'aba_number',
            'cash_account'
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Enter account name...')
            }),
            'account_number': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Enter account number...')
            }),
            'routing_number': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Enter routing number...')
            }),
            'aba_number': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Enter ABA number...')
            }),
            'account_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'cash_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            })
        }
        labels = {
            'name': _('Account Name'),
            'account_number': _('Account Number'),
            'account_type': _('Account Type'),
            'cash_account': _('Cash Account'),
            'aba_number': _('ABA Number'),
            'routing_number': _('Routing Number'),
        }
