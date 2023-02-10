from django.forms import ModelForm, TextInput, Select

from django_ledger.io.roles import GROUP_INCOME, ASSET_CA_INVENTORY, GROUP_EXPENSES, GROUP_COGS, COGS
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
    PRODUCT_OR_SERVICE_ROLES = GROUP_INCOME + GROUP_COGS
    PRODUCT_OR_SERVICE_ROLES.append(ASSET_CA_INVENTORY)

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)

        accounts_qs = AccountModel.objects.with_roles(
            roles=self.PRODUCT_OR_SERVICE_ROLES,
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL).active()

        # caches the QS for filtering...
        len(accounts_qs)

        self.fields['earnings_account'].queryset = accounts_qs.filter(role__in=GROUP_INCOME)
        self.fields['cogs_account'].queryset = accounts_qs.filter(role__in=GROUP_COGS)
        self.fields['inventory_account'].queryset = accounts_qs.filter(role__in=[ASSET_CA_INVENTORY])

        uom_qs = UnitOfMeasureModel.objects.for_entity_active(
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
            'item_type',
            'default_amount',
            'earnings_account',
            'cogs_account',
            'inventory_account'
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'uom': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'item_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'earnings_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'cogs_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'inventory_account': Select(attrs={
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

    def clean(self):
        item_model: ItemModel = self.instance
        item_model.is_product_or_service = True
        return super().clean()


class ProductOrServiceCreateForm(ProductOrServiceUpdateForm):
    class Meta(ProductOrServiceUpdateForm.Meta):
        fields = [
            'name',
            'sku',
            'upc',
            'item_id',
            'uom',
            'item_type',
            'default_amount',
            'earnings_account',
            'cogs_account',
            'inventory_account'
        ]


class ExpenseItemUpdateForm(ModelForm):
    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)

        accounts_qs = AccountModel.objects.with_roles(
            roles=GROUP_EXPENSES,
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL).active()

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
            'item_type',
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
            'item_type': Select(attrs={
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


class InventoryItemUpdateForm(ModelForm):
    # INVENTORY_ROLES = [ASSET_CA_INVENTORY] + GROUP_COGS

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)

        accounts_qs = AccountModel.objects.with_roles(
            roles=[ASSET_CA_INVENTORY],
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL).active()
        self.fields['inventory_account'].queryset = accounts_qs

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
            'item_type',
            'upc',
            'item_id',
            'default_amount',
            'inventory_account',
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'uom': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'item_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'inventory_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'earnings_account': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'cogs_account': Select(attrs={
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

    model = ItemModel


class InventoryItemCreateForm(InventoryItemUpdateForm):

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        super().__init__(entity_slug=entity_slug, user_model=user_model, *args, **kwargs)
        uom_qs = UnitOfMeasureModel.objects.for_entity_active(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )
        self.fields['uom'].queryset = uom_qs
