"""
Enterprise accounting models for medium-company workflows.

These models add governance, period controls, reconciliation, tax, multi-currency,
payments, dimensions, budgets, fixed assets, documents, and integration primitives
without changing the existing ledger core.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Manager, Q, QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.models.deprecations import deprecated_entity_slug_behavior
from django_ledger.models.mixins import CreateUpdateMixIn
from django_ledger.models.utils import lazy_loader


class EnterpriseModelValidationError(ValidationError):
    pass


class EnterpriseModelQuerySet(QuerySet):
    def for_user(self, user_model) -> 'EnterpriseModelQuerySet':
        if user_model.is_superuser:
            return self
        return self.filter(
            Q(entity_model__admin=user_model) |
            Q(entity_model__managers__in=[user_model]) |
            Q(entity_model__entityrolemodel__user=user_model, entity_model__entityrolemodel__active=True)
        ).distinct()

    def active(self) -> 'EnterpriseModelQuerySet':
        if 'active' in {f.name for f in self.model._meta.fields}:
            return self.filter(active=True)
        return self

    def status(self, *statuses) -> 'EnterpriseModelQuerySet':
        if not statuses:
            return self
        if 'status' in {f.name for f in self.model._meta.fields}:
            return self.filter(status__in=statuses)
        return self

    def date_range(self, field_name: str, from_date=None, to_date=None) -> 'EnterpriseModelQuerySet':
        qs = self
        if from_date:
            qs = qs.filter(**{f'{field_name}__gte': from_date})
        if to_date:
            qs = qs.filter(**{f'{field_name}__lte': to_date})
        return qs


class EnterpriseModelManager(Manager):
    def get_queryset(self) -> EnterpriseModelQuerySet:
        return EnterpriseModelQuerySet(self.model, using=self._db)

    @deprecated_entity_slug_behavior
    def for_entity(self, entity_model: 'EntityModel | str | UUID' = None, **kwargs) -> EnterpriseModelQuerySet:  # noqa: F821
        EntityModel = lazy_loader.get_entity_model()
        qs = self.get_queryset()
        user_model = kwargs.get('user_model')
        if user_model:
            qs = qs.for_user(user_model=user_model)

        if isinstance(entity_model, EntityModel):
            return qs.filter(entity_model=entity_model)
        if isinstance(entity_model, str):
            return qs.filter(entity_model__slug__exact=entity_model)
        if isinstance(entity_model, UUID):
            return qs.filter(entity_model_id=entity_model)
        raise EnterpriseModelValidationError(_('Must pass EntityModel, entity slug, or entity UUID.'))


class EnterpriseBaseModel(CreateUpdateMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity_model = models.ForeignKey('django_ledger.EntityModel', on_delete=models.CASCADE)

    objects = EnterpriseModelManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['entity_model']),
        ]

    @property
    def entity_slug(self):
        try:
            return self._entity_slug
        except AttributeError:
            return self.entity_model.slug


class GenericTargetMixin(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, null=True, blank=True)
    object_id = models.CharField(max_length=64, null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]


class AuditEventModel(EnterpriseBaseModel, GenericTargetMixin):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_STATE = 'state'
    ACTION_APPROVE = 'approve'
    ACTION_POST = 'post'
    ACTION_LOCK = 'lock'
    ACTION_EXPORT = 'export'
    ACTION_IMPORT = 'import'
    ACTION_CHOICES = [
        (ACTION_CREATE, _('Create')),
        (ACTION_UPDATE, _('Update')),
        (ACTION_DELETE, _('Delete')),
        (ACTION_STATE, _('State Change')),
        (ACTION_APPROVE, _('Approve')),
        (ACTION_POST, _('Post')),
        (ACTION_LOCK, _('Lock')),
        (ACTION_EXPORT, _('Export')),
        (ACTION_IMPORT, _('Import')),
    ]
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    object_repr = models.CharField(max_length=255, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    request_meta = models.JSONField(default=dict, blank=True)
    correlation_id = models.UUIDField(default=uuid4, db_index=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        ordering = ['-created']
        indexes = EnterpriseBaseModel.Meta.indexes + [
            models.Index(fields=['entity_model', 'action', 'created']),
            models.Index(fields=['correlation_id']),
        ]

    def save(self, *args, **kwargs):
        if self.pk and self.__class__.objects.filter(pk=self.pk).exists():
            raise EnterpriseModelValidationError(_('Audit events are immutable.'))
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise EnterpriseModelValidationError(_('Audit events cannot be deleted.'))


class EntityRoleModel(EnterpriseBaseModel):
    ROLE_OWNER = 'owner'
    ROLE_FINANCE_ADMIN = 'finance_admin'
    ROLE_ACCOUNTANT = 'accountant'
    ROLE_APPROVER = 'approver'
    ROLE_AUDITOR = 'auditor'
    ROLE_READ_ONLY = 'read_only'
    ROLE_INTEGRATION = 'integration'
    ROLE_CHOICES = [
        (ROLE_OWNER, _('Owner')),
        (ROLE_FINANCE_ADMIN, _('Finance Admin')),
        (ROLE_ACCOUNTANT, _('Accountant')),
        (ROLE_APPROVER, _('Approver')),
        (ROLE_AUDITOR, _('Auditor')),
        (ROLE_READ_ONLY, _('Read Only')),
        (ROLE_INTEGRATION, _('Integration User')),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    active = models.BooleanField(default=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(fields=['entity_model', 'user', 'role'], name='unique_entity_user_role')
        ]
        indexes = EnterpriseBaseModel.Meta.indexes + [
            models.Index(fields=['user', 'role', 'active']),
        ]


class ApprovalPolicyModel(EnterpriseBaseModel):
    DOCUMENT_ALL = 'all'
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=150)
    document_type = models.CharField(max_length=50, default=DOCUMENT_ALL)
    min_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    max_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    account_role = models.CharField(max_length=30, blank=True)
    vendor = models.ForeignKey('django_ledger.VendorModel', on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey('django_ledger.CustomerModel', on_delete=models.SET_NULL, null=True, blank=True)
    entity_unit = models.ForeignKey('django_ledger.EntityUnitModel', on_delete=models.SET_NULL, null=True, blank=True)
    required_role = models.CharField(max_length=32, choices=EntityRoleModel.ROLE_CHOICES, default=EntityRoleModel.ROLE_APPROVER)
    required_approvals = models.PositiveSmallIntegerField(default=1)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        indexes = EnterpriseBaseModel.Meta.indexes + [
            models.Index(fields=['entity_model', 'active', 'document_type']),
        ]


class ApprovalRequestModel(EnterpriseBaseModel, GenericTargetMixin):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELED = 'canceled'
    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_REJECTED, _('Rejected')),
        (STATUS_CANCELED, _('Canceled')),
    ]
    policy = models.ForeignKey(ApprovalPolicyModel, on_delete=models.PROTECT, null=True, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_requests_created')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    reason = models.TextField(blank=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        indexes = EnterpriseBaseModel.Meta.indexes + [
            models.Index(fields=['entity_model', 'status', 'created']),
        ]

    def approve(self, user_model, note: str = '', commit: bool = False):
        ApprovalStepModel.objects.create(
            entity_model=self.entity_model,
            approval_request=self,
            actor=user_model,
            action=ApprovalStepModel.ACTION_APPROVE,
            note=note,
        )
        if self.approvalstepmodel_set.filter(action=ApprovalStepModel.ACTION_APPROVE).count() >= self.required_approvals:
            self.status = self.STATUS_APPROVED
            if commit:
                self.save(update_fields=['status', 'updated'])
        return self

    @property
    def required_approvals(self):
        return self.policy.required_approvals if self.policy_id else 1


class ApprovalStepModel(EnterpriseBaseModel):
    ACTION_APPROVE = 'approve'
    ACTION_REJECT = 'reject'
    ACTION_COMMENT = 'comment'
    ACTION_CHOICES = [
        (ACTION_APPROVE, _('Approve')),
        (ACTION_REJECT, _('Reject')),
        (ACTION_COMMENT, _('Comment')),
    ]
    approval_request = models.ForeignKey(ApprovalRequestModel, on_delete=models.CASCADE)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    note = models.TextField(blank=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        indexes = EnterpriseBaseModel.Meta.indexes + [
            models.Index(fields=['approval_request', 'action']),
        ]


class AccountingPeriodModel(EnterpriseBaseModel):
    STATUS_OPEN = 'open'
    STATUS_SOFT_CLOSED = 'soft_closed'
    STATUS_CLOSED = 'closed'
    STATUS_REOPENED = 'reopened'
    STATUS_CHOICES = [
        (STATUS_OPEN, _('Open')),
        (STATUS_SOFT_CLOSED, _('Soft Closed')),
        (STATUS_CLOSED, _('Closed')),
        (STATUS_REOPENED, _('Reopened')),
    ]
    fiscal_year = models.IntegerField()
    period = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    reopen_reason = models.TextField(blank=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(fields=['entity_model', 'fiscal_year', 'period'], name='unique_entity_accounting_period')
        ]
        indexes = EnterpriseBaseModel.Meta.indexes + [
            models.Index(fields=['entity_model', 'status', 'start_date', 'end_date']),
        ]

    def contains_date(self, dt):
        return self.start_date <= dt <= self.end_date

    def is_locked(self):
        return self.status in [self.STATUS_SOFT_CLOSED, self.STATUS_CLOSED]


class CloseTaskModel(EnterpriseBaseModel):
    accounting_period = models.ForeignKey(AccountingPeriodModel, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        ordering = ['sort_order', 'name']


class BankStatementModel(EnterpriseBaseModel):
    STATUS_IMPORTED = 'imported'
    STATUS_RECONCILING = 'reconciling'
    STATUS_RECONCILED = 'reconciled'
    STATUS_LOCKED = 'locked'
    STATUS_VOID = 'void'
    STATUS_CHOICES = [
        (STATUS_IMPORTED, _('Imported')),
        (STATUS_RECONCILING, _('Reconciling')),
        (STATUS_RECONCILED, _('Reconciled')),
        (STATUS_LOCKED, _('Locked')),
        (STATUS_VOID, _('Void')),
    ]
    bank_account = models.ForeignKey('django_ledger.BankAccountModel', on_delete=models.CASCADE)
    statement_id = models.CharField(max_length=120, blank=True)
    date_start = models.DateField()
    date_end = models.DateField()
    opening_balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    closing_balance = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_IMPORTED)
    source = models.CharField(max_length=20, blank=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(fields=['entity_model', 'bank_account', 'statement_id'], name='unique_bank_statement_id')
        ]


class BankStatementLineModel(EnterpriseBaseModel):
    statement_model = models.ForeignKey(BankStatementModel, on_delete=models.CASCADE)
    posted_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    payee = models.CharField(max_length=255, blank=True)
    memo = models.TextField(blank=True)
    reference = models.CharField(max_length=120, blank=True)
    matched_transaction = models.ForeignKey('django_ledger.TransactionModel', on_delete=models.SET_NULL, null=True, blank=True)
    ignored = models.BooleanField(default=False)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        indexes = EnterpriseBaseModel.Meta.indexes + [
            models.Index(fields=['statement_model', 'posted_date']),
            models.Index(fields=['entity_model', 'amount', 'posted_date']),
        ]


class BankReconciliationModel(EnterpriseBaseModel):
    STATUS_DRAFT = 'draft'
    STATUS_REVIEW = 'in_review'
    STATUS_RECONCILED = 'reconciled'
    STATUS_LOCKED = 'locked'
    STATUS_VOID = 'void'
    STATUS_CHOICES = [
        (STATUS_DRAFT, _('Draft')),
        (STATUS_REVIEW, _('In Review')),
        (STATUS_RECONCILED, _('Reconciled')),
        (STATUS_LOCKED, _('Locked')),
        (STATUS_VOID, _('Void')),
    ]
    statement_model = models.ForeignKey(BankStatementModel, on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    reconciled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)


class TaxAuthorityModel(EnterpriseBaseModel):
    name = models.CharField(max_length=150)
    jurisdiction = models.CharField(max_length=100, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)


class TaxCodeModel(EnterpriseBaseModel):
    TAX_OUTPUT = 'output'
    TAX_INPUT = 'input'
    TAX_EXEMPT = 'exempt'
    TAX_ZERO = 'zero'
    TAX_REVERSE = 'reverse'
    TAX_WITHHOLDING = 'withholding'
    TAX_CHOICES = [
        (TAX_OUTPUT, _('Output Tax')),
        (TAX_INPUT, _('Input Tax')),
        (TAX_EXEMPT, _('Exempt')),
        (TAX_ZERO, _('Zero Rated')),
        (TAX_REVERSE, _('Reverse Charge')),
        (TAX_WITHHOLDING, _('Withholding')),
    ]
    authority = models.ForeignKey(TaxAuthorityModel, on_delete=models.PROTECT)
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    tax_type = models.CharField(max_length=16, choices=TAX_CHOICES)
    active = models.BooleanField(default=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(fields=['entity_model', 'code'], name='unique_entity_tax_code')
        ]


class TaxRateModel(EnterpriseBaseModel):
    tax_code = models.ForeignKey(TaxCodeModel, on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=9, decimal_places=6, validators=[MinValueValidator(Decimal('0.00'))])
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        ordering = ['-effective_date']


class TaxLineModel(EnterpriseBaseModel, GenericTargetMixin):
    tax_code = models.ForeignKey(TaxCodeModel, on_delete=models.PROTECT)
    tax_rate = models.ForeignKey(TaxRateModel, on_delete=models.PROTECT, null=True, blank=True)
    taxable_amount = models.DecimalField(max_digits=20, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2)
    inclusive = models.BooleanField(default=False)
    filing_period = models.ForeignKey(AccountingPeriodModel, on_delete=models.SET_NULL, null=True, blank=True)


class CurrencyModel(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=80)
    symbol = models.CharField(max_length=8, blank=True)
    decimal_places = models.PositiveSmallIntegerField(default=2)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class ExchangeRateModel(EnterpriseBaseModel):
    from_currency = models.ForeignKey(CurrencyModel, on_delete=models.PROTECT, related_name='exchange_rates_from')
    to_currency = models.ForeignKey(CurrencyModel, on_delete=models.PROTECT, related_name='exchange_rates_to')
    rate = models.DecimalField(max_digits=20, decimal_places=10, validators=[MinValueValidator(Decimal('0.00'))])
    rate_date = models.DateField()
    source = models.CharField(max_length=80, blank=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(fields=['entity_model', 'from_currency', 'to_currency', 'rate_date'], name='unique_exchange_rate')
        ]
        ordering = ['-rate_date']


class PaymentModel(EnterpriseBaseModel):
    PAYMENT_AR = 'ar'
    PAYMENT_AP = 'ap'
    DIRECTION_CHOICES = [
        (PAYMENT_AR, _('Accounts Receivable')),
        (PAYMENT_AP, _('Accounts Payable')),
    ]
    STATUS_DRAFT = 'draft'
    STATUS_APPROVED = 'approved'
    STATUS_POSTED = 'posted'
    STATUS_VOID = 'void'
    STATUS_CHOICES = [
        (STATUS_DRAFT, _('Draft')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_POSTED, _('Posted')),
        (STATUS_VOID, _('Void')),
    ]
    direction = models.CharField(max_length=2, choices=DIRECTION_CHOICES)
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    unapplied_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    currency = models.ForeignKey(CurrencyModel, on_delete=models.PROTECT, null=True, blank=True)
    base_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    bank_account = models.ForeignKey('django_ledger.BankAccountModel', on_delete=models.PROTECT, null=True, blank=True)
    customer = models.ForeignKey('django_ledger.CustomerModel', on_delete=models.PROTECT, null=True, blank=True)
    vendor = models.ForeignKey('django_ledger.VendorModel', on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    reference = models.CharField(max_length=120, blank=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        indexes = EnterpriseBaseModel.Meta.indexes + [
            models.Index(fields=['entity_model', 'direction', 'status', 'payment_date']),
        ]


class PaymentAllocationModel(EnterpriseBaseModel, GenericTargetMixin):
    payment = models.ForeignKey(PaymentModel, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    write_off_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))


class CreditNoteModel(EnterpriseBaseModel):
    customer = models.ForeignKey('django_ledger.CustomerModel', on_delete=models.PROTECT)
    invoice = models.ForeignKey('django_ledger.InvoiceModel', on_delete=models.SET_NULL, null=True, blank=True)
    note_number = models.CharField(max_length=30, blank=True)
    note_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    unapplied_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=16, default='draft')


class DebitNoteModel(EnterpriseBaseModel):
    vendor = models.ForeignKey('django_ledger.VendorModel', on_delete=models.PROTECT)
    bill = models.ForeignKey('django_ledger.BillModel', on_delete=models.SET_NULL, null=True, blank=True)
    note_number = models.CharField(max_length=30, blank=True)
    note_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    unapplied_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=16, default='draft')


class DimensionModel(EnterpriseBaseModel):
    DIMENSION_DEPARTMENT = 'department'
    DIMENSION_PROJECT = 'project'
    DIMENSION_LOCATION = 'location'
    DIMENSION_COST_CENTER = 'cost_center'
    DIMENSION_PRODUCT_LINE = 'product_line'
    DIMENSION_CHOICES = [
        (DIMENSION_DEPARTMENT, _('Department')),
        (DIMENSION_PROJECT, _('Project')),
        (DIMENSION_LOCATION, _('Location')),
        (DIMENSION_COST_CENTER, _('Cost Center')),
        (DIMENSION_PRODUCT_LINE, _('Product Line')),
    ]
    name = models.CharField(max_length=100)
    dimension_type = models.CharField(max_length=32, choices=DIMENSION_CHOICES)
    active = models.BooleanField(default=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(fields=['entity_model', 'dimension_type', 'name'], name='unique_dimension_name')
        ]


class DimensionValueModel(EnterpriseBaseModel):
    dimension = models.ForeignKey(DimensionModel, on_delete=models.CASCADE)
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    active = models.BooleanField(default=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(fields=['dimension', 'code'], name='unique_dimension_value_code')
        ]


class DimensionAssignmentModel(EnterpriseBaseModel, GenericTargetMixin):
    dimension_value = models.ForeignKey(DimensionValueModel, on_delete=models.PROTECT)
    weight = models.DecimalField(max_digits=9, decimal_places=6, default=Decimal('1.00'))


class BudgetModel(EnterpriseBaseModel):
    name = models.CharField(max_length=150)
    fiscal_year = models.IntegerField()
    status = models.CharField(max_length=16, default='draft')

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(fields=['entity_model', 'name', 'fiscal_year'], name='unique_budget_year_name')
        ]


class BudgetVersionModel(EnterpriseBaseModel):
    budget = models.ForeignKey(BudgetModel, on_delete=models.CASCADE)
    version = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=16, default='draft')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta(EnterpriseBaseModel.Meta):
        abstract = False
        constraints = [
            models.UniqueConstraint(fields=['budget', 'version'], name='unique_budget_version')
        ]


class BudgetLineModel(EnterpriseBaseModel):
    budget_version = models.ForeignKey(BudgetVersionModel, on_delete=models.CASCADE)
    account_model = models.ForeignKey('django_ledger.AccountModel', on_delete=models.PROTECT)
    accounting_period = models.ForeignKey(AccountingPeriodModel, on_delete=models.PROTECT, null=True, blank=True)
    entity_unit = models.ForeignKey('django_ledger.EntityUnitModel', on_delete=models.PROTECT, null=True, blank=True)
    dimension_value = models.ForeignKey(DimensionValueModel, on_delete=models.PROTECT, null=True, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)


class AllocationRuleModel(EnterpriseBaseModel):
    name = models.CharField(max_length=150)
    source_account = models.ForeignKey('django_ledger.AccountModel', on_delete=models.PROTECT, related_name='allocation_sources')
    active = models.BooleanField(default=True)


class AllocationRuleLineModel(EnterpriseBaseModel):
    allocation_rule = models.ForeignKey(AllocationRuleModel, on_delete=models.CASCADE)
    target_account = models.ForeignKey('django_ledger.AccountModel', on_delete=models.PROTECT, related_name='allocation_targets')
    dimension_value = models.ForeignKey(DimensionValueModel, on_delete=models.PROTECT, null=True, blank=True)
    percentage = models.DecimalField(max_digits=9, decimal_places=6)


class InventoryValuationPolicyModel(EnterpriseBaseModel):
    METHOD_FIFO = 'fifo'
    METHOD_WEIGHTED_AVERAGE = 'weighted_average'
    METHOD_STANDARD = 'standard'
    METHOD_CHOICES = [
        (METHOD_FIFO, _('FIFO')),
        (METHOD_WEIGHTED_AVERAGE, _('Weighted Average')),
        (METHOD_STANDARD, _('Standard Cost')),
    ]
    name = models.CharField(max_length=150)
    method = models.CharField(max_length=32, choices=METHOD_CHOICES)
    active = models.BooleanField(default=True)


class InventoryAdjustmentModel(EnterpriseBaseModel):
    STATUS_DRAFT = 'draft'
    STATUS_POSTED = 'posted'
    STATUS_VOID = 'void'
    STATUS_CHOICES = [
        (STATUS_DRAFT, _('Draft')),
        (STATUS_POSTED, _('Posted')),
        (STATUS_VOID, _('Void')),
    ]
    adjustment_date = models.DateField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    reason = models.CharField(max_length=255, blank=True)


class InventoryAdjustmentLineModel(EnterpriseBaseModel):
    adjustment = models.ForeignKey(InventoryAdjustmentModel, on_delete=models.CASCADE)
    item_model = models.ForeignKey('django_ledger.ItemModel', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=20, decimal_places=4, default=Decimal('0.00'))
    entity_unit = models.ForeignKey('django_ledger.EntityUnitModel', on_delete=models.PROTECT, null=True, blank=True)


class AssetCategoryModel(EnterpriseBaseModel):
    name = models.CharField(max_length=150)
    asset_account = models.ForeignKey('django_ledger.AccountModel', on_delete=models.PROTECT, related_name='fixed_asset_categories')
    depreciation_account = models.ForeignKey('django_ledger.AccountModel', on_delete=models.PROTECT, related_name='depreciation_categories')
    accumulated_depreciation_account = models.ForeignKey('django_ledger.AccountModel', on_delete=models.PROTECT, related_name='accumulated_depreciation_categories')


class DepreciationMethodModel(EnterpriseBaseModel):
    METHOD_STRAIGHT_LINE = 'straight_line'
    METHOD_CHOICES = [
        (METHOD_STRAIGHT_LINE, _('Straight Line')),
    ]
    name = models.CharField(max_length=150)
    method = models.CharField(max_length=32, choices=METHOD_CHOICES, default=METHOD_STRAIGHT_LINE)
    useful_life_months = models.PositiveIntegerField()


class FixedAssetModel(EnterpriseBaseModel):
    STATUS_ACTIVE = 'active'
    STATUS_DISPOSED = 'disposed'
    STATUS_IMPAIRED = 'impaired'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, _('Active')),
        (STATUS_DISPOSED, _('Disposed')),
        (STATUS_IMPAIRED, _('Impaired')),
    ]
    asset_number = models.CharField(max_length=30, blank=True)
    name = models.CharField(max_length=150)
    category = models.ForeignKey(AssetCategoryModel, on_delete=models.PROTECT)
    depreciation_method = models.ForeignKey(DepreciationMethodModel, on_delete=models.PROTECT)
    acquisition_date = models.DateField()
    acquisition_cost = models.DecimalField(max_digits=20, decimal_places=2)
    salvage_value = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)


class DepreciationScheduleModel(EnterpriseBaseModel):
    fixed_asset = models.ForeignKey(FixedAssetModel, on_delete=models.CASCADE)
    period = models.ForeignKey(AccountingPeriodModel, on_delete=models.PROTECT)
    depreciation_amount = models.DecimalField(max_digits=20, decimal_places=2)
    posted = models.BooleanField(default=False)
    journal_entry = models.ForeignKey('django_ledger.JournalEntryModel', on_delete=models.SET_NULL, null=True, blank=True)


class AssetDisposalModel(EnterpriseBaseModel):
    fixed_asset = models.ForeignKey(FixedAssetModel, on_delete=models.PROTECT)
    disposal_date = models.DateField()
    proceeds = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal('0.00'))
    journal_entry = models.ForeignKey('django_ledger.JournalEntryModel', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)


def document_attachment_upload_to(instance, filename):
    return f'django_ledger/documents/{instance.entity_model_id}/{filename}'


class DocumentAttachmentModel(EnterpriseBaseModel, GenericTargetMixin):
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to=document_attachment_upload_to)
    original_filename = models.CharField(max_length=255, blank=True)
    checksum = models.CharField(max_length=128, blank=True, db_index=True)
    mime_type = models.CharField(max_length=120, blank=True)
    retention_date = models.DateField(null=True, blank=True)
    ocr_payload = models.JSONField(default=dict, blank=True)


class WebhookEndpointModel(EnterpriseBaseModel):
    name = models.CharField(max_length=150)
    url = models.URLField()
    secret = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)
    event_types = models.JSONField(default=list, blank=True)


class WebhookDeliveryModel(EnterpriseBaseModel):
    endpoint = models.ForeignKey(WebhookEndpointModel, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    delivered = models.BooleanField(default=False)
    attempt_count = models.PositiveSmallIntegerField(default=0)


class IntegrationCredentialModel(EnterpriseBaseModel):
    name = models.CharField(max_length=150)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=128)
    active = models.BooleanField(default=True)
    scopes = models.JSONField(default=list, blank=True)

    def get_absolute_url(self):
        return reverse('django_ledger:entity-dashboard', kwargs={'entity_slug': self.entity_slug})
