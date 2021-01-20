from django.forms import ModelForm, TextInput, Select, HiddenInput

from django_ledger.io.roles import GROUP_INCOME, GROUP_EXPENSES
from django_ledger.models import AccountModel, ItemModel, UnitOfMeasureModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


class UnitOfMeasureModelCreateForm(ModelForm):

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)

    class Meta:
        model = UnitOfMeasureModel
        fields = [
            'name',
            'unit_abbr',
            'is_active'
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'unit_abbr': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            })
        }


class UnitOfMeasureModelUpdateForm(UnitOfMeasureModelCreateForm):
    pass


class ProductOrServiceUpdateForm(ModelForm):

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)

        accounts_qs = AccountModel.on_coa.with_roles(
            roles=GROUP_INCOME,
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL)
        self.fields['earnings_account'].queryset = accounts_qs.filter(role__in=GROUP_INCOME)

        uom_qs = UnitOfMeasureModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )
        self.fields['uom'].queryset = uom_qs

    class Meta:
        model = ItemModel
        fields = [
            'name',
            'sku',
            'upc',
            'item_id',
            'uom',
            'default_amount',
            'earnings_account',
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'uom': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'earnings_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'sku': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'upc': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'item_id': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'default_amount': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }


class ProductOrServiceCreateForm(ProductOrServiceUpdateForm):

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        super().__init__(entity_slug=entity_slug, user_model=user_model, *args, **kwargs)
        uom_qs = UnitOfMeasureModel.objects.for_entity_active(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )
        self.fields['uom'].queryset = uom_qs
        self.fields['is_product_or_service'].initial = True

    class Meta(ProductOrServiceUpdateForm.Meta):
        fields = [
            'name',
            'sku',
            'upc',
            'item_id',
            'uom',
            'default_amount',
            'earnings_account',
            'is_product_or_service'
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'uom': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'earnings_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'sku': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'upc': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'item_id': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'default_amount': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'is_product_or_service': HiddenInput(attrs={
                'readonly': True
            })
        }


class ExpenseItemUpdateForm(ModelForm):
    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)

        accounts_qs = AccountModel.on_coa.with_roles(
            roles=GROUP_EXPENSES,
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL)
        self.fields['expense_account'].queryset = accounts_qs.filter(role__in=GROUP_EXPENSES)

        uom_qs = UnitOfMeasureModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )
        self.fields['uom'].queryset = uom_qs

    class Meta:
        model = ItemModel
        fields = [
            'name',
            'uom',
            'default_amount',
            'expense_account',
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'uom': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'expense_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'sku': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'upc': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'item_id': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'default_amount': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }


class ExpenseItemCreateForm(ExpenseItemUpdateForm):

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        super().__init__(entity_slug=entity_slug, user_model=user_model, *args, **kwargs)
        uom_qs = UnitOfMeasureModel.objects.for_entity_active(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )
        self.fields['uom'].queryset = uom_qs
