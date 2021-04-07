from django.forms import (ModelForm, DateInput, TextInput, Select, CheckboxInput, BaseModelFormSet,
                          modelformset_factory)
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_RECEIVABLES, LIABILITY_CL_ACC_PAYABLE, GROUP_EXPENSES
from django_ledger.models import (ItemModel, AccountModel, BillModel, BillModelItemsThroughModel,
                                  VendorModel)
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
        self.fields['prepaid_account'].queryset = account_qs.filter(role__exact=ASSET_CA_RECEIVABLES)
        self.fields['unearned_account'].queryset = account_qs.filter(role__exact=LIABILITY_CL_ACC_PAYABLE)

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
            'terms',

            'cash_account',
            'prepaid_account',
            'unearned_account',

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
            'prepaid_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'unearned_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
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
            'accrue'
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
            'accrue': CheckboxInput(attrs={'type': 'checkbox'}),
            'paid': CheckboxInput(attrs={'type': 'checkbox'}),
        }


class BillItemForm(ModelForm):
    class Meta:
        model = BillModelItemsThroughModel
        fields = [
            'item_model',
            'unit_cost',
            'entity_unit',
            'quantity'
        ]
        widgets = {
            'item_model': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            }),
            'entity_unit': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            }),
            'unit_cost': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            }),
            'quantity': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
            })
        }


class BaseInvoiceItemFormset(BaseModelFormSet):

    def __init__(self, *args, entity_slug, bill_pk, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.BILL_PK = bill_pk
        self.ENTITY_SLUG = entity_slug

        items_qs = ItemModel.objects.expenses(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        self.LN = len(items_qs)  # evaluate the QS and cache results...
        for form in self.forms:
            form.fields['item_model'].queryset = items_qs


BillItemFormset = modelformset_factory(
    model=BillModelItemsThroughModel,
    form=BillItemForm,
    formset=BaseInvoiceItemFormset,
    can_delete=True,
    extra=5
)
