from django.forms import ModelForm, DateInput, TextInput, Select, EmailInput, URLInput, CheckboxInput
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_RECEIVABLES, LIABILITY_CL_ACC_PAYABLE, GROUP_INCOME
from django_ledger.models.accounts import AccountModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


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
            'invoice_to',
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
            'terms': _('Invoice Terms')
        }
        widgets = {
            'date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Invoice Date (YYYY-MM-DD)...')
            }),
            'amount_due': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': '$$$'}),
            'terms': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small'
            }),
            'invoice_to': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
                'placeholder': _('Invoice To...')
            }),
            'address_1': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
                'placeholder': _('Address line 1...')
            }),
            'address_2': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
                'placeholder': _('City, State, ZIP...')
            }),
            'phone': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
                'placeholder': _('Phone number...')
            }),
            'email': EmailInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
                'placeholder': _('Customer email...')
            }),
            'website': URLInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
                'placeholder': _('Customer website...')
            }),

            'cash_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'receivable_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'payable_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'earnings_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
        }


class InvoiceModelUpdateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

    def save(self, commit=True):
        if commit:
            self.instance.migrate_state(
                user_model=self.USER_MODEL,
                entity_slug=self.ENTITY_SLUG
            )
        super().save(commit=commit)

    class Meta:
        model = InvoiceModel
        fields = [
            'amount_due',
            'amount_paid',
            'paid',
            'paid_date',
            'progress',
            'progressible'
        ]
        labels = {
            'progress': _('Progress Amount 0.00 -> 1.00 (percent)')
        }
        widgets = {

            'date': DateInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'amount_due': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES, 'placeholder': '$$$'}),
            'terms': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'paid_date': DateInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'placeholder': _('Paid Date (YYYY-MM-DD)...')}
            ),
            'amount_paid': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
                }),
            'progress': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'progressible': CheckboxInput(attrs={'type': 'checkbox'}),
            'paid': CheckboxInput(attrs={'type': 'checkbox'}),

        }
