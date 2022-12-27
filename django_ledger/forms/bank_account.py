from django.forms import ModelForm, TextInput, Select, ValidationError
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
        account_qs = AccountModel.objects.for_entity_available(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG).filter(
            role__exact=ASSET_CA_CASH)
        self.fields['cash_account'].queryset = account_qs

    def clean(self):
        cash_account = self.cleaned_data['cash_account']
        routing_number = self.cleaned_data['routing_number']
        account_number = self.cleaned_data['account_number']

        if not cash_account:
            raise ValidationError('Must select a bank account.')

        # catching unique database constraint...
        if BankAccountModel.objects.filter(
                cash_account=cash_account,
                routing_number__exact=routing_number,
                account_number__exact=account_number
        ).exists():
            raise ValidationError('Duplicate bank account model.')

    class Meta:
        model = BankAccountModel
        fields = [
            'name',
            'account_type',
            'account_number',
            'routing_number',
            'aba_number',
            'swift_number',
            'cash_account',
            'active'
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
            'swift_number': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Enter SWIFT number...')
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
            'active': _('Make Active'),
        }


class BankAccountUpdateForm(BankAccountCreateForm):
    class Meta:
        model = BankAccountModel
        fields = [
            'name',
            'account_type',
            'cash_account',
            'active'
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Enter account name...')
            }),
            'account_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'cash_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            })
        }

    def clean(self):
        cash_account = self.cleaned_data['cash_account']

        if not cash_account:
            raise ValidationError('Must select a bank account.')

        # catching unique database constraint...
        if 'cash_account' in self.changed_data:
            if BankAccountModel.objects.filter(
                    cash_account=cash_account,
                    routing_number__exact=self.instance.routing_number,
                    account_number__exact=self.instance.account_number
            ).exists():
                raise ValidationError('Duplicate bank account model.')
