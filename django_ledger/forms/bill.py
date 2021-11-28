from django.forms import (ModelForm, DateInput, TextInput, Select, CheckboxInput, BaseModelFormSet,
                          modelformset_factory)
from django.utils.translation import gettext_lazy as _
from django.forms import ValidationError

from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_DEFERRED_REVENUE
from django_ledger.models import (ItemModel, AccountModel, BillModel, ItemThroughModel,
                                  VendorModel)
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class BillModelCreateForm(ModelForm):
    def __init__(self, *args, entity_slug, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        self.get_vendor_queryset()
        self.get_accounts_queryset()

    def get_vendor_queryset(self):

        if 'vendor' in self.fields:
            vendor_qs = VendorModel.objects.for_entity(
                user_model=self.USER_MODEL,
                entity_slug=self.ENTITY_SLUG
            )
            self.fields['vendor'].queryset = vendor_qs

    def get_accounts_queryset(self):

        if all([
            'cash_account' in self.fields,
            'prepaid_account' in self.fields,
            'unearned_account' in self.fields,
        ]):
            account_qs = AccountModel.on_coa.for_bill(
                user_model=self.USER_MODEL,
                entity_slug=self.ENTITY_SLUG
            )

            # forcing evaluation of qs to cache results for fields... (avoids multiple database queries)
            len(account_qs)

            self.fields['cash_account'].queryset = account_qs.filter(role__exact=ASSET_CA_CASH)
            self.fields['prepaid_account'].queryset = account_qs.filter(role__exact=ASSET_CA_PREPAID)
            self.fields['unearned_account'].queryset = account_qs.filter(role__exact=LIABILITY_CL_DEFERRED_REVENUE)

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


class BillModelUpdateForm(BillModelCreateForm):

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
            'cash_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-danger'}),
            'prepaid_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-danger'}),
            'unearned_account': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-danger'}),
        }
        labels = {
            'progress': 'Bill Progress Amount (%)'
        }


class BillModelConfigureForm(BillModelUpdateForm):
    class Meta(BillModelUpdateForm.Meta):
        fields = [
            'xref',
            'amount_due',
            'amount_paid',
            'paid',
            'paid_date',
            'progress',
            'accrue',
            'cash_account',
            'prepaid_account',
            'unearned_account',
        ]


class BillItemForm(ModelForm):

    def clean(self):
        cleaned_data = super(BillItemForm, self).clean()
        bill_item_model: ItemThroughModel = self.instance
        if bill_item_model.po_model is not None:
            quantity = cleaned_data['quantity']
            if quantity > bill_item_model.po_quantity:
                raise ValidationError(f'Cannot bill more than {bill_item_model.po_quantity} authorized.')
        return cleaned_data

    class Meta:
        model = ItemThroughModel
        fields = [
            'item_model',
            'unit_cost',
            'entity_unit',
            'quantity',
        ]
        widgets = {
            'item_model': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'entity_unit': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'unit_cost': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            }),
            'quantity': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
            })
        }


class BaseBillItemFormset(BaseModelFormSet):

    def __init__(self, *args, entity_slug, bill_pk, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.BILL_PK = bill_pk
        self.ENTITY_SLUG = entity_slug

        items_qs = ItemModel.objects.for_bill(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        for form in self.forms:
            form.fields['item_model'].queryset = items_qs
            instance: ItemThroughModel = form.instance
            if instance.po_model_id:
                form.fields['item_model'].disabled = True
                form.fields['entity_unit'].disabled = True


BillItemFormset = modelformset_factory(
    model=ItemThroughModel,
    form=BillItemForm,
    formset=BaseBillItemFormset,
    can_delete=True,
    extra=5
)
