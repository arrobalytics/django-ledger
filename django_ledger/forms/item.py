from django.forms import ModelForm, TextInput, Select, ChoiceField
from django.utils.translation import gettext_lazy as _

from django_ledger.io.roles import GROUP_INCOME, ASSET_CA_INVENTORY, GROUP_EXPENSES, GROUP_COGS
from django_ledger.models import AccountModel, ItemModel, UnitOfMeasureModel
from django_ledger.settings import DJANGO_LEDGER_FORM_INPUT_CLASSES


# #### UNIT OF MEASURES #######
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


# #### PRODUCT ITEMS #######

class ProductCreateForm(ModelForm):
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

        if 'uom' in self.fields:
            uom_qs = UnitOfMeasureModel.objects.for_entity_active(
                entity_slug=self.ENTITY_SLUG,
                user_model=self.USER_MODEL
            )
            self.fields['uom'].queryset = uom_qs

        if 'item_type' in self.fields:
            self.fields['item_type'].choices = ItemModel.ITEM_TYPE_CHOICES_PRODUCT

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
            'cogs_account',
            'inventory_account',
            'sold_as_unit'
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
            'item_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'default_amount': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }
        labels = {
            'name': _('Product Name'),
            'item_type': _('Product Type')
        }

    def clean(self):
        item_model: ItemModel = self.instance
        item_model.item_role = ItemModel.ITEM_ROLE_PRODUCT
        return super().clean()


class ProductUpdateForm(ProductCreateForm):
    pass


# #### SERVICE ITEMS #######

class ServiceCreateForm(ModelForm):
    SERVICE_ROLES = GROUP_INCOME + GROUP_COGS

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)

        accounts_qs = AccountModel.objects.with_roles(
            roles=self.SERVICE_ROLES,
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL).active()

        # caches the QS for filtering...
        len(accounts_qs)

        self.fields['earnings_account'].queryset = accounts_qs.filter(role__in=GROUP_INCOME)
        self.fields['cogs_account'].queryset = accounts_qs.filter(role__in=GROUP_COGS)

        if 'uom' in self.fields:
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
            'default_amount',
            'earnings_account',
            'cogs_account',
            'sold_as_unit'
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
            'item_type': Select(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'default_amount': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }
        labels = {
            'name': _('Service Name'),
            'sold_as_unit': _('Sold as Unit?')
        }

    def clean(self):
        item_model: ItemModel = self.instance
        item_model.item_role = ItemModel.ITEM_ROLE_SERVICE
        return super().clean()


class ServiceUpdateForm(ServiceCreateForm):
    pass


# #### EXPENSE ITEMS #######
class ExpenseItemCreateForm(ModelForm):
    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)

        accounts_qs = AccountModel.objects.with_roles(
            roles=GROUP_EXPENSES,
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL).active()

        self.fields['expense_account'].queryset = accounts_qs.filter(role__in=GROUP_EXPENSES)

        if 'uom' in self.fields:
            uom_qs = UnitOfMeasureModel.objects.for_entity(
                entity_slug=self.ENTITY_SLUG,
                user_model=self.USER_MODEL
            )
            self.fields['uom'].queryset = uom_qs

    class Meta:
        model = ItemModel
        fields = [
            'name',
            'upc',
            'sku',
            'uom',
            'item_type',
            'default_amount',
            'expense_account',
        ]
        widgets = {
            'name': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('The item name...')
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
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES,
                'placeholder': _('The UPC code of the item, if any...')
            }),
            'item_id': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'default_amount': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }
        labels = {
            'name': _('Expense Name')
        }

    def clean(self):
        item_model: ItemModel = self.instance
        item_model.item_role = ItemModel.ITEM_ROLE_EXPENSE
        return super().clean()


class ExpenseItemUpdateForm(ExpenseItemCreateForm):
    class Meta(ExpenseItemCreateForm.Meta):
        fields = [
            'name',
            'upc',
            'sku',
            'default_amount',
            'expense_account',
        ]


# #### INVENTORY ITEMS #######
class InventoryItemCreateForm(ModelForm):

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)

        accounts_qs = AccountModel.objects.with_roles(
            roles=[ASSET_CA_INVENTORY],
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL).active()
        self.fields['inventory_account'].queryset = accounts_qs

        if 'uom' in self.fields:
            uom_qs = UnitOfMeasureModel.objects.for_entity_active(
                entity_slug=self.ENTITY_SLUG,
                user_model=self.USER_MODEL
            )
            self.fields['uom'].queryset = uom_qs

    class Meta:
        model = ItemModel
        fields = [
            'name',
            'uom',
            'upc',
            'sku',
            'item_id',
            'item_type',
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
            'sku': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'item_id': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
            'default_amount': TextInput(attrs={
                'class': DJANGO_LEDGER_FORM_INPUT_CLASSES
            }),
        }
        labels = {
            'name': _('Inventory Name')
        }

    def clean(self):
        item_model: ItemModel = self.instance
        item_model.item_role = ItemModel.ITEM_ROLE_INVENTORY
        return super().clean()


class InventoryItemUpdateForm(InventoryItemCreateForm):
    class Meta(InventoryItemCreateForm.Meta):
        fields = [
            'name',
            'upc',
            'sku',
            'item_id',
            'default_amount',
            'inventory_account',
        ]
