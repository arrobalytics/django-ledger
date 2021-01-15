from django.forms import ModelForm, TextInput, Select, HiddenInput

from django_ledger.io.roles import INCOME_SALES
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


class ProductOrServiceCreateForm(ModelForm):
    # PRODUCT_ACCOUNT_ROLES: list = [COGS, ASSET_CA_INVENTORY, INCOME_SALES]

    def __init__(self, entity_slug: str, user_model, *args, **kwargs):
        self.ENTITY_SLUG = entity_slug
        self.USER_MODEL = user_model
        super().__init__(*args, **kwargs)

        accounts_qs = AccountModel.on_coa.with_roles(
            roles=[INCOME_SALES],
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL)

        uom_qs = UnitOfMeasureModel.objects.for_entity(
            entity_slug=self.ENTITY_SLUG,
            user_model=self.USER_MODEL
        )

        self.fields['earnings_account'].queryset = accounts_qs.filter(role__iexact=INCOME_SALES)
        self.fields['uom'].queryset = uom_qs
        self.fields['is_product_or_service'].initial = True

    def clean_is_product_or_service(self):
        return True

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
            'is_product_or_service',
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


class ProductOrServiceUpdateForm(ProductOrServiceCreateForm):
    pass
