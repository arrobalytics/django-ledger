from django.forms import ModelForm, DateInput, TextInput, Select, EmailInput, URLInput, CheckboxInput
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_RECEIVABLES, LIABILITY_CL_ACC_PAYABLE, GROUP_EXPENSES
from django_ledger.models.accounts import AccountModel
from django_ledger.models.bill import BillModel
from django_ledger.models.vendor import VendorModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class BillModelCreateForm(ModelForm):

    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

        account_qs = AccountModel.on_coa.for_entity_available(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG
        )

        # forcing evaluation of qs to cache results for fields... (avoids 4 database queries, vs 1)
        len(account_qs)
        self.fields['cash_account'].queryset = account_qs.filter(role__exact=ASSET_CA_CASH)
        self.fields['receivable_account'].queryset = account_qs.filter(role__exact=ASSET_CA_RECEIVABLES)
        self.fields['payable_account'].queryset = account_qs.filter(role__exact=LIABILITY_CL_ACC_PAYABLE)
        self.fields['earnings_account'].queryset = account_qs.filter(role__in=GROUP_EXPENSES)

        vendor_qs = VendorModel.objects.for_entity(
            user_model=self.USER_MODEL,
            entity_slug=self.ENTITY_SLUG
        )
        self.fields['vendor'].queryset = vendor_qs

    class Meta:
        model = BillModel
        fields = [
            'vendor',

            'xref',
            'date',
            'amount_due',
            'terms',

            'cash_account',
            'receivable_account',
            'payable_account',
            'earnings_account',

        ]
        widgets = {
            'date': DateInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('Bill Date (YYYY-MM-DD)...')
            }),
            'amount_due': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': '$$$'}),
            'xref': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                'placeholder': 'External Reference Number...'}),
            'terms': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small'
            }),
            'vendor': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),

            'cash_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'receivable_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'payable_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'earnings_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
        }


class BillModelUpdateForm(ModelForm):

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
        model = BillModel
        fields = [
            'xref',
            'amount_due',
            'amount_paid',
            'paid',
            'paid_date',
            'progress',
            'progressible'
        ]
        widgets = {
            'xref': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                                     'placeholder': 'External Reference...'}),
            'date': DateInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'amount_due': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES, 'placeholder': '$$$'}),
            'terms': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'paid_date': DateInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'placeholder': _('Date (YYYY-MM-DD)...')}
            ),
            'amount_paid': TextInput(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                }),
            'progress': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'progressible': CheckboxInput(attrs={'type': 'checkbox'}),
            'paid': CheckboxInput(attrs={'type': 'checkbox'}),
        }
