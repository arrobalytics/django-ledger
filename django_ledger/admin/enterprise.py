from django.contrib import admin

from django_ledger.models.enterprise import (
    AccountingPeriodModel,
    AllocationRuleLineModel,
    AllocationRuleModel,
    ApprovalPolicyModel,
    ApprovalRequestModel,
    ApprovalStepModel,
    AssetCategoryModel,
    AssetDisposalModel,
    AuditEventModel,
    BankReconciliationModel,
    BankStatementLineModel,
    BankStatementModel,
    BudgetLineModel,
    BudgetModel,
    BudgetVersionModel,
    CloseTaskModel,
    CreditNoteModel,
    CurrencyModel,
    DebitNoteModel,
    DepreciationMethodModel,
    DepreciationScheduleModel,
    DimensionAssignmentModel,
    DimensionModel,
    DimensionValueModel,
    DocumentAttachmentModel,
    EntityRoleModel,
    ExchangeRateModel,
    FixedAssetModel,
    IntegrationCredentialModel,
    InventoryAdjustmentLineModel,
    InventoryAdjustmentModel,
    InventoryValuationPolicyModel,
    PaymentAllocationModel,
    PaymentModel,
    TaxAuthorityModel,
    TaxCodeModel,
    TaxLineModel,
    TaxRateModel,
    WebhookDeliveryModel,
    WebhookEndpointModel,
)


class EntityScopedAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'entity_model', 'created', 'updated']
    search_fields = ['entity_model__name', 'entity_model__slug']
    list_filter = ['entity_model']
    readonly_fields = ['uuid', 'created', 'updated']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(qs, 'for_user'):
            return qs.for_user(request.user)
        return qs


@admin.register(AuditEventModel)
class AuditEventModelAdmin(EntityScopedAdmin):
    list_display = ['created', 'entity_model', 'action', 'actor', 'content_type', 'object_id', 'correlation_id']
    list_filter = ['entity_model', 'action', 'content_type']
    search_fields = ['object_repr', 'object_id', 'actor__username', 'correlation_id']
    readonly_fields = EntityScopedAdmin.readonly_fields + [
        'actor',
        'action',
        'content_type',
        'object_id',
        'object_repr',
        'before',
        'after',
        'request_meta',
        'correlation_id',
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


for model in [
    AccountingPeriodModel,
    AllocationRuleLineModel,
    AllocationRuleModel,
    ApprovalPolicyModel,
    ApprovalRequestModel,
    ApprovalStepModel,
    AssetCategoryModel,
    AssetDisposalModel,
    BankReconciliationModel,
    BankStatementLineModel,
    BankStatementModel,
    BudgetLineModel,
    BudgetModel,
    BudgetVersionModel,
    CloseTaskModel,
    CreditNoteModel,
    DebitNoteModel,
    DepreciationMethodModel,
    DepreciationScheduleModel,
    DimensionAssignmentModel,
    DimensionModel,
    DimensionValueModel,
    DocumentAttachmentModel,
    EntityRoleModel,
    ExchangeRateModel,
    FixedAssetModel,
    IntegrationCredentialModel,
    InventoryAdjustmentLineModel,
    InventoryAdjustmentModel,
    InventoryValuationPolicyModel,
    PaymentAllocationModel,
    PaymentModel,
    TaxAuthorityModel,
    TaxCodeModel,
    TaxLineModel,
    TaxRateModel,
    WebhookDeliveryModel,
    WebhookEndpointModel,
]:
    admin.site.register(model, EntityScopedAdmin)


@admin.register(CurrencyModel)
class CurrencyModelAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'decimal_places', 'active']
    search_fields = ['code', 'name']
    list_filter = ['active']
