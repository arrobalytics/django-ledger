from django.forms import (ModelForm, DateInput, TextInput, Select,
                          CheckboxInput, BaseModelFormSet,
                          modelformset_factory, Textarea)
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import ASSET_CA_CASH, ASSET_CA_PREPAID, LIABILITY_CL_DEFERRED_REVENUE
from django_ledger.models import (ItemModel, AccountModel, BillModel, ItemThroughModel,
                                  VendorModel, EntityUnitModel)
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
                'placeholder': _('Bill Date (YYYY-MM-DD)...'),
                'id': 'djl-bill-date-input'
            }),
            'amount_due': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': '$$$',
                'id': 'djl-bill-amount-due-input'}),
            'xref': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-large',
                'placeholder': 'External Reference Number...',
                'id': 'djl-bill-xref-input'
            }),
            'terms': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES + ' is-small',
                'id': 'djl-bill-create-terms-select-input'
            }),
            'vendor': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'id': 'djl-bill-create-vendor-select-input'
            }),

            'cash_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'id': 'djl-bill-cash-account-input'
            }),
            'prepaid_account': Select(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'id': 'djl-bill-prepaid-account-input'
                }),
            'unearned_account': Select(
                attrs={
                    'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                    'id': 'djl-bill-unearned-account-input'
                }),
        }


class BillModelUpdateForm(BillModelCreateForm):

    def __init__(self,
                 *args,
                 entity_slug,
                 user_model,
                 **kwargs):
        super().__init__(entity_slug=entity_slug, user_model=user_model, *args, **kwargs)
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model

        bill_model: BillModel = self.instance

        if any([
            bill_model.bill_status != BillModel.BILL_STATUS_APPROVED,
            bill_model.paid,
            bill_model.bill_status == BillModel.BILL_STATUS_CANCELED
        ]):
            self.fields['amount_paid'].disabled = True
            self.fields['paid'].disabled = True
            self.fields['paid_date'].disabled = True
            self.fields['progress'].disabled = True

        if any([
            bill_model.bill_status != BillModel.BILL_STATUS_DRAFT,
            bill_model.paid,
            bill_model.bill_status == BillModel.BILL_STATUS_CANCELED
        ]):
            self.fields['terms'].disabled = True
            self.fields['accrue'].disabled = True
            self.fields['xref'].disabled = True

        if bill_model.bill_status == BillModel.BILL_STATUS_APPROVED:
            self.fields['bill_status'].disabled = True

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
            'accrue',
            'bill_status',
            'terms',
            'markdown_notes'
        ]
        widgets = {
            'xref': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                                     'placeholder': 'External Reference...'}),
            'date': DateInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'amount_due': TextInput(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES, 'placeholder': '$$$'}),
            'terms': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
            'bill_status': Select(attrs={'class': DJANGO_LEDGER_FORM_INPUT_CLASSES}),
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
            'markdown_notes': Textarea(attrs={
                'class': 'textarea'
            })
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

    def __init__(self, *args, entity_slug, bill_model: BillModel, user_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.USER_MODEL = user_model
        self.BILL_MODEL = bill_model
        self.ENTITY_SLUG = entity_slug

        items_qs = ItemModel.objects.for_bill(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        unit_qs = EntityUnitModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        for form in self.forms:
            form.fields['item_model'].queryset = items_qs
            form.fields['entity_unit'].queryset = unit_qs

            if not self.BILL_MODEL.can_edit_items():
                form.fields['item_model'].disabled = True
                form.fields['quantity'].disabled = True
                form.fields['unit_cost'].disabled = True
                form.fields['entity_unit'].disabled = True

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
