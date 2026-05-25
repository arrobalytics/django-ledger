from django.contrib import admin

from django_ledger_extensions.models import (
    AccountTranslationModel,
    EntityTaxProfile,
    ItemTranslationModel,
    SupportingDocumentModel,
)


@admin.register(EntityTaxProfile)
class EntityTaxProfileAdmin(admin.ModelAdmin):
    list_display = ('entity', 'tax_regime', 'default_vat_rate', 'vat_id')
    search_fields = ('entity__name', 'vat_id')


@admin.register(SupportingDocumentModel)
class SupportingDocumentAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'document_type', 'content_type', 'object_id', 'immutable', 'created')
    list_filter = ('document_type', 'immutable')
    readonly_fields = ('checksum', 'created', 'updated')


@admin.register(AccountTranslationModel)
class AccountTranslationAdmin(admin.ModelAdmin):
    list_display = ('account', 'locale', 'name')
    list_filter = ('locale',)


@admin.register(ItemTranslationModel)
class ItemTranslationAdmin(admin.ModelAdmin):
    list_display = ('item', 'locale', 'name', 'regional_code')
    list_filter = ('locale',)
