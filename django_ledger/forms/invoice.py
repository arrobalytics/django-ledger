from django.forms import ModelForm, DateInput, TextInput, Select, EmailInput, URLInput
from django.utils.translation import gettext_lazy as _l

from django_ledger.forms import DJETLER_FORM_INPUT_CLASS
from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_RECEIVABLES, LIABILITY_CL_ACC_PAYABLE, GROUP_INCOME
from django_ledger.models import InvoiceModel, AccountModel


class InvoiceModelCreateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        account_qs = AccountModel.on_coa.for_entity_available(user_model=self.USER_MODEL,
                                                              entity_slug=self.ENTITY_SLUG)

        self.fields['cash_account'].queryset = account_qs.filter(role__exact=ASSET_CA_CASH)
        self.fields['receivable_account'].queryset = account_qs.filter(role__exact=ASSET_CA_RECEIVABLES)
        self.fields['payable_account'].queryset = account_qs.filter(role__exact=LIABILITY_CL_ACC_PAYABLE)
        self.fields['earnings_account'].queryset = account_qs.filter(role__in=GROUP_INCOME)

    class Meta:
        model = InvoiceModel
        fields = [
            'date',
            'amount_due',
            'terms',
            'subject_name',
            'address_1',
            'address_2',
            'phone',
            'email',
            'website',
            'cash_account',
            'receivable_account',
            'payable_account',
            'earnings_account'
        ]
        labels = {
            'terms': _l('Invoice Terms')
        }
        widgets = {
            'date': DateInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS,
                'placeholder': _l('Date (MM-DD-YYYY)...')
            }),
            'amount_due': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS,
                'placeholder': '$$$'}),
            'terms': Select(attrs={
                'class': DJETLER_FORM_INPUT_CLASS + ' is-small'
            }),

            'subject_name': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS + ' is-small',
                'placeholder': _l('Customer name...')
            }),

            'address_1': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS + ' is-small',
                'placeholder': _l('Address line 1...')
            }),
            'address_2': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS + ' is-small',
                'placeholder': _l('Address line 2...')
            }),
            'phone': TextInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS + ' is-small',
                'placeholder': _l('Phone number...')
            }),
            'email': EmailInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS + ' is-small',
                'placeholder': _l('Customer email...')
            }),
            'website': URLInput(attrs={
                'class': DJETLER_FORM_INPUT_CLASS + ' is-small',
                'placeholder': _l('Customer website...')
            }),

            'cash_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'receivable_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'payable_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'earnings_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
        }


class InvoiceModelUpdateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

    def save(self, commit=True):
        super().save(commit=commit)
        if commit:
            self.instance.migrate_state(
                user_model=self.USER_MODEL,
                entity_slug=self.ENTITY_SLUG
            )

    class Meta:
        model = InvoiceModel
        fields = [
            'subject_name',
            'address_1',
            'address_2',
            'phone',
            'email',
            'website',
            'date',
            'terms',
            'amount_due',
            'amount_paid',
            'paid',
            'paid_date',
            'progress',
            'progressible'
        ]
        widgets = {
            'subject_name': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'address_1': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'address_2': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'phone': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'email': EmailInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'website': URLInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),

            'date': DateInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'paid_date': DateInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'amount_due': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'amount_paid': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'terms': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),

            'progress': TextInput(attrs={'class': DJETLER_FORM_INPUT_CLASS}),

            'cash_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'receivable_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'payable_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
            'earnings_account': Select(attrs={'class': DJETLER_FORM_INPUT_CLASS}),
        }
