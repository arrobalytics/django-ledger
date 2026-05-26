from django.contrib import admin

from django_ledger_extensions.models import (
    AccountTranslationModel,
    DocumentInboxItem,
    EntityTaxProfile,
    ExternalPaymentRecord,
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


@admin.register(DocumentInboxItem)
class DocumentInboxItemAdmin(admin.ModelAdmin):
    list_display = (
        'uuid',
        'entity',
        'status',
        'source',
        'document_type',
        'suggested_amount',
        'suggested_date',
        'external_source',
        'external_id',
        'created',
    )
    list_filter = ('status', 'source', 'document_type')
    search_fields = ('description', 'vendor_name', 'reference', 'external_id')
    readonly_fields = ('checksum', 'linked_content_type', 'linked_object_id', 'created', 'updated')


@admin.register(ExternalPaymentRecord)
class ExternalPaymentRecordAdmin(admin.ModelAdmin):
    list_display = (
        'uuid',
        'entity',
        'provider',
        'external_id',
        'amount',
        'currency',
        'paid_at',
        'status',
        'invoice',
    )
    list_filter = ('provider', 'status')
    search_fields = ('external_id', 'customer_email', 'customer_name', 'description')
    readonly_fields = ('error_message', 'created', 'updated')


@admin.register(AccountTranslationModel)
class AccountTranslationAdmin(admin.ModelAdmin):
    list_display = ('account', 'locale', 'name')
    list_filter = ('locale',)


@admin.register(ItemTranslationModel)
class ItemTranslationAdmin(admin.ModelAdmin):
    list_display = ('item', 'locale', 'name', 'regional_code')
    list_filter = ('locale',)
