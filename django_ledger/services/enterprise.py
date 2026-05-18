"""
Service-layer APIs for medium-company accounting workflows.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
from typing import Iterable, Optional

from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from django_ledger.models.enterprise import (
    AccountingPeriodModel,
    AllocationRuleModel,
    ApprovalPolicyModel,
    ApprovalRequestModel,
    AssetDisposalModel,
    AuditEventModel,
    BankReconciliationModel,
    BankStatementLineModel,
    BankStatementModel,
    BudgetVersionModel,
    CreditNoteModel,
    DebitNoteModel,
    DepreciationScheduleModel,
    DimensionAssignmentModel,
    DimensionValueModel,
    DocumentAttachmentModel,
    EnterpriseModelValidationError,
    ExchangeRateModel,
    EntityRoleModel,
    FixedAssetModel,
    IntegrationCredentialModel,
    PaymentAllocationModel,
    PaymentModel,
    TaxLineModel,
    TaxRateModel,
    WebhookDeliveryModel,
    WebhookEndpointModel,
)


def lazy_transaction_model():
    return apps.get_model('django_ledger', 'TransactionModel')


def _target_kwargs(target):
    if not target:
        return {}
    return {
        'content_type': ContentType.objects.get_for_model(target, for_concrete_model=False),
        'object_id': str(target.pk),
        'object_repr': str(target),
    }


def _get_target_policy_context(target) -> dict:
    account_roles = set()
    account_candidates = [
        'account',
        'account_model',
        'cash_account',
        'prepaid_account',
        'unearned_account',
        'asset_account',
        'depreciation_account',
        'accumulated_depreciation_account',
        'source_account',
        'target_account',
    ]
    for attr_name in account_candidates:
        account_model = getattr(target, attr_name, None)
        account_role = getattr(account_model, 'role', '') if account_model else ''
        if account_role:
            account_roles.add(account_role)

    return {
        'document_type': target.__class__.__name__.lower(),
        'vendor': getattr(target, 'vendor', None),
        'customer': getattr(target, 'customer', None),
        'entity_unit': getattr(target, 'entity_unit', None),
        'account_roles': account_roles,
    }


def _policy_specificity(policy: ApprovalPolicyModel) -> tuple:
    return (
        int(policy.document_type != ApprovalPolicyModel.DOCUMENT_ALL),
        int(policy.vendor_id is not None),
        int(policy.customer_id is not None),
        int(policy.entity_unit_id is not None),
        int(bool(policy.account_role)),
        int(policy.min_amount is not None),
        int(policy.max_amount is not None),
        policy.min_amount or Decimal('0.00'),
    )


def create_audit_event(
    *,
    entity_model,
    action: str,
    actor=None,
    target=None,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    request_meta: Optional[dict] = None,
    correlation_id=None,
) -> AuditEventModel:
    kwargs = _target_kwargs(target)
    if correlation_id:
        kwargs['correlation_id'] = correlation_id
    return AuditEventModel.objects.create(
        entity_model=entity_model,
        action=action,
        actor=actor,
        before=before or {},
        after=after or {},
        request_meta=request_meta or {},
        **kwargs,
    )


def require_entity_role(user_model, entity_model, *roles):
    if user_model.is_superuser or entity_model.admin_id == user_model.id:
        return True
    if not roles:
        return entity_model.managers.filter(pk=user_model.pk).exists()
    if entity_model.entityrolemodel_set.filter(user=user_model, role__in=roles, active=True).exists():
        return True
    raise EnterpriseModelValidationError('User does not have the required entity role.')


def require_report_access(user_model, entity_model):
    return require_entity_role(
        user_model,
        entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
        EntityRoleModel.ROLE_ACCOUNTANT,
        EntityRoleModel.ROLE_APPROVER,
        EntityRoleModel.ROLE_AUDITOR,
        EntityRoleModel.ROLE_READ_ONLY,
        EntityRoleModel.ROLE_INTEGRATION,
    )


def require_integration_access(*, entity_model, token_hash: str, scope: str = '') -> IntegrationCredentialModel:
    credential = IntegrationCredentialModel.objects.for_entity(entity_model).filter(
        token_hash=token_hash,
        active=True,
    ).first()
    if not credential:
        raise EnterpriseModelValidationError('Invalid integration credential.')
    if scope and scope not in (credential.scopes or []):
        raise EnterpriseModelValidationError('Integration credential does not include the required scope.')
    return credential


def get_target_entity(target):
    for attr_name in ('entity_model', 'entity'):
        entity_model = getattr(target, attr_name, None)
        if entity_model is not None:
            return entity_model
    ledger_model = getattr(target, 'ledger', None) or getattr(target, 'ledger_model', None)
    if ledger_model is not None:
        return getattr(ledger_model, 'entity', None)
    journal_entry = getattr(target, 'journal_entry', None)
    if journal_entry is not None and getattr(journal_entry, 'ledger', None) is not None:
        return journal_entry.ledger.entity
    raise EnterpriseModelValidationError('Unable to resolve target entity.')


def request_approval(*, entity_model, target, requested_by=None, amount=None, reason: str = '') -> ApprovalRequestModel:
    target_context = _get_target_policy_context(target)
    policies = ApprovalPolicyModel.objects.for_entity(entity_model).active().filter(
        document_type__in=[target_context['document_type'], ApprovalPolicyModel.DOCUMENT_ALL],
    )
    if amount is not None:
        policies = policies.filter(
            Q(min_amount__isnull=True) | Q(min_amount__lte=amount),
            Q(max_amount__isnull=True) | Q(max_amount__gte=amount),
        )
    vendor = target_context['vendor']
    customer = target_context['customer']
    entity_unit = target_context['entity_unit']
    account_roles = target_context['account_roles']

    if vendor is not None:
        policies = policies.filter(Q(vendor__isnull=True) | Q(vendor=vendor))
    else:
        policies = policies.filter(vendor__isnull=True)

    if customer is not None:
        policies = policies.filter(Q(customer__isnull=True) | Q(customer=customer))
    else:
        policies = policies.filter(customer__isnull=True)

    if entity_unit is not None:
        policies = policies.filter(Q(entity_unit__isnull=True) | Q(entity_unit=entity_unit))
    else:
        policies = policies.filter(entity_unit__isnull=True)

    if account_roles:
        policies = policies.filter(Q(account_role='') | Q(account_role__in=account_roles))
    else:
        policies = policies.filter(account_role='')

    policy = max(policies, key=_policy_specificity, default=None)
    kwargs = _target_kwargs(target)
    kwargs.pop('object_repr', None)
    approval_request = ApprovalRequestModel.objects.create(
        entity_model=entity_model,
        policy=policy,
        requested_by=requested_by,
        amount=amount,
        reason=reason,
        **kwargs,
    )
    create_audit_event(
        entity_model=entity_model,
        action=AuditEventModel.ACTION_APPROVE,
        actor=requested_by,
        target=target,
        after={'approval_request': str(approval_request.uuid), 'status': approval_request.status},
    )
    return approval_request


def post_document(*, entity_model, target, user_model=None, posting_date=None, verify: bool = True):
    require_entity_role(
        user_model,
        entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
        EntityRoleModel.ROLE_ACCOUNTANT,
    )
    posting_date = posting_date or getattr(target, 'date', None) or getattr(target, 'timestamp', None) or timezone.localdate()
    if hasattr(posting_date, 'date'):
        posting_date = posting_date.date()
    assert_period_open(entity_model, posting_date)
    before = {
        'posted': bool(getattr(target, 'posted', False)),
        'status': getattr(target, 'status', ''),
    }
    if hasattr(target, 'mark_as_posted'):
        target.mark_as_posted(commit=True, verify=verify, raise_exception=True)
    elif hasattr(target, 'post'):
        target.post(commit=True)
    else:
        raise EnterpriseModelValidationError('Target does not expose a supported posting method.')
    create_audit_event(
        entity_model=entity_model,
        action=AuditEventModel.ACTION_POST,
        actor=user_model,
        target=target,
        before=before,
        after={
            'posted': bool(getattr(target, 'posted', False)),
            'status': getattr(target, 'status', ''),
        },
    )
    return target


def approve_document(*, approval_request: ApprovalRequestModel, user_model, note: str = '') -> ApprovalRequestModel:
    required_role = EntityRoleModel.ROLE_APPROVER
    if approval_request.policy_id:
        required_role = approval_request.policy.required_role
    require_entity_role(
        user_model,
        approval_request.entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
        required_role,
    )
    with transaction.atomic():
        approval_request.approve(user_model=user_model, note=note, commit=True)
        create_audit_event(
            entity_model=approval_request.entity_model,
            action=AuditEventModel.ACTION_APPROVE,
            actor=user_model,
            target=approval_request.content_object,
            after={'approval_request': str(approval_request.uuid), 'status': approval_request.status},
        )
    return approval_request


def close_period(*, accounting_period: AccountingPeriodModel, user_model, soft: bool = False) -> AccountingPeriodModel:
    require_entity_role(
        user_model,
        accounting_period.entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
    )
    incomplete_tasks = accounting_period.closetaskmodel_set.filter(completed=False).exists()
    if incomplete_tasks:
        raise EnterpriseModelValidationError('Cannot close an accounting period with incomplete close tasks.')
    before = {'status': accounting_period.status}
    accounting_period.status = AccountingPeriodModel.STATUS_SOFT_CLOSED if soft else AccountingPeriodModel.STATUS_CLOSED
    accounting_period.closed_by = user_model
    accounting_period.closed_at = timezone.now()
    accounting_period.save(update_fields=['status', 'closed_by', 'closed_at', 'updated'])
    create_audit_event(
        entity_model=accounting_period.entity_model,
        action=AuditEventModel.ACTION_LOCK,
        actor=user_model,
        target=accounting_period,
        before=before,
        after={'status': accounting_period.status},
    )
    return accounting_period


def reopen_period(*, accounting_period: AccountingPeriodModel, user_model, reason: str) -> AccountingPeriodModel:
    require_entity_role(
        user_model,
        accounting_period.entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
    )
    before = {'status': accounting_period.status}
    accounting_period.status = AccountingPeriodModel.STATUS_REOPENED
    accounting_period.reopen_reason = reason
    accounting_period.save(update_fields=['status', 'reopen_reason', 'updated'])
    create_audit_event(
        entity_model=accounting_period.entity_model,
        action=AuditEventModel.ACTION_STATE,
        actor=user_model,
        target=accounting_period,
        before=before,
        after={'status': accounting_period.status, 'reason': reason},
    )
    return accounting_period


def assert_period_open(entity_model, dt: date):
    period = AccountingPeriodModel.objects.for_entity(entity_model).filter(
        start_date__lte=dt,
        end_date__gte=dt,
    ).first()
    if period and period.is_locked():
        raise EnterpriseModelValidationError(f'Accounting period {period.fiscal_year}-{period.period} is closed.')
    return period


def import_bank_statement_lines(*, statement_model: BankStatementModel, rows: Iterable[dict]) -> list[BankStatementLineModel]:
    created_lines = []
    for row in rows:
        created_lines.append(BankStatementLineModel.objects.create(
            entity_model=statement_model.entity_model,
            statement_model=statement_model,
            posted_date=row['posted_date'],
            amount=row['amount'],
            payee=row.get('payee', ''),
            memo=row.get('memo', ''),
            reference=row.get('reference', ''),
        ))
    return created_lines


def import_bank_statement_csv(*, statement_model: BankStatementModel, csv_text: str) -> list[BankStatementLineModel]:
    reader = csv.DictReader(StringIO(csv_text))
    rows = []
    for row in reader:
        posted_date = row.get('posted_date') or row.get('date')
        if not posted_date:
            raise EnterpriseModelValidationError('Statement CSV must include posted_date or date.')
        rows.append({
            'posted_date': date.fromisoformat(posted_date),
            'amount': Decimal(row['amount']),
            'payee': row.get('payee', ''),
            'memo': row.get('memo', '') or row.get('description', ''),
            'reference': row.get('reference', ''),
        })
    created_lines = import_bank_statement_lines(statement_model=statement_model, rows=rows)
    create_audit_event(
        entity_model=statement_model.entity_model,
        action=AuditEventModel.ACTION_IMPORT,
        target=statement_model,
        after={'source': 'csv', 'line_count': len(created_lines)},
    )
    return created_lines


def get_bank_match_candidates(*, statement_line: BankStatementLineModel, date_window_days: int = 3):
    posted_date = statement_line.posted_date
    start = posted_date - timedelta(days=date_window_days)
    end = posted_date + timedelta(days=date_window_days)
    transaction_model = lazy_transaction_model()
    amount = statement_line.amount
    amount_candidates = {amount, -amount, abs(amount)}
    qs = transaction_model.objects.for_entity(entity_model=statement_line.entity_model).filter(
        amount__in=amount_candidates,
        journal_entry__timestamp__date__gte=start,
        journal_entry__timestamp__date__lte=end,
        reconciled=False,
    ).select_related('journal_entry', 'account')
    if statement_line.reference:
        reference_q = Q(pk=statement_line.reference) | Q(journal_entry__description__icontains=statement_line.reference)
        if statement_line.memo:
            reference_q |= Q(journal_entry__description__icontains=statement_line.memo[:80])
        qs = qs.filter(reference_q)
    return qs.order_by('journal_entry__timestamp')


def auto_match_bank_statement(*, statement_model: BankStatementModel, user_model=None, date_window_days: int = 3) -> list[BankStatementLineModel]:
    matched = []
    for statement_line in statement_model.bankstatementlinemodel_set.filter(matched_transaction__isnull=True, ignored=False):
        candidates = list(get_bank_match_candidates(statement_line=statement_line, date_window_days=date_window_days)[:1])
        if candidates:
            matched.append(match_bank_statement_line(
                statement_line=statement_line,
                transaction_model=candidates[0],
                user_model=user_model,
            ))
    return matched


def unmatch_bank_statement_line(*, statement_line: BankStatementLineModel, user_model=None) -> BankStatementLineModel:
    transaction_model = statement_line.matched_transaction
    before = {'matched_transaction': str(statement_line.matched_transaction_id) if statement_line.matched_transaction_id else ''}
    if transaction_model:
        transaction_model.__class__.objects.filter(pk=transaction_model.pk).update(
            reconciled=False,
            updated=timezone.now(),
        )
    statement_line.matched_transaction = None
    statement_line.save(update_fields=['matched_transaction', 'updated'])
    create_audit_event(
        entity_model=statement_line.entity_model,
        action=AuditEventModel.ACTION_STATE,
        actor=user_model,
        target=statement_line,
        before=before,
        after={'matched_transaction': ''},
    )
    return statement_line


def ignore_bank_statement_line(*, statement_line: BankStatementLineModel, user_model=None, reason: str = '') -> BankStatementLineModel:
    before = {'ignored': statement_line.ignored}
    statement_line.ignored = True
    statement_line.save(update_fields=['ignored', 'updated'])
    create_audit_event(
        entity_model=statement_line.entity_model,
        action=AuditEventModel.ACTION_STATE,
        actor=user_model,
        target=statement_line,
        before=before,
        after={'ignored': True, 'reason': reason},
    )
    return statement_line


def lock_reconciliation(*, reconciliation: BankReconciliationModel, user_model=None) -> BankReconciliationModel:
    if reconciliation.status != BankReconciliationModel.STATUS_RECONCILED:
        raise EnterpriseModelValidationError('Only reconciled statements can be locked.')
    before = {'status': reconciliation.status}
    reconciliation.status = BankReconciliationModel.STATUS_LOCKED
    reconciliation.statement_model.status = BankStatementModel.STATUS_LOCKED
    reconciliation.statement_model.save(update_fields=['status', 'updated'])
    reconciliation.save(update_fields=['status', 'updated'])
    create_audit_event(
        entity_model=reconciliation.entity_model,
        action=AuditEventModel.ACTION_LOCK,
        actor=user_model,
        target=reconciliation.statement_model,
        before=before,
        after={'status': reconciliation.status},
    )
    return reconciliation


def void_reconciliation(*, reconciliation: BankReconciliationModel, user_model=None, reason: str = '') -> BankReconciliationModel:
    before = {'status': reconciliation.status}
    reconciliation.status = BankReconciliationModel.STATUS_VOID
    reconciliation.statement_model.status = BankStatementModel.STATUS_VOID
    reconciliation.statement_model.save(update_fields=['status', 'updated'])
    reconciliation.save(update_fields=['status', 'updated'])
    create_audit_event(
        entity_model=reconciliation.entity_model,
        action=AuditEventModel.ACTION_STATE,
        actor=user_model,
        target=reconciliation.statement_model,
        before=before,
        after={'status': reconciliation.status, 'reason': reason},
    )
    return reconciliation


def reconcile_statement(*, statement_model: BankStatementModel, user_model=None) -> BankReconciliationModel:
    reconciliation, _ = BankReconciliationModel.objects.get_or_create(
        entity_model=statement_model.entity_model,
        statement_model=statement_model,
        defaults={'status': BankReconciliationModel.STATUS_DRAFT},
    )
    unmatched = statement_model.bankstatementlinemodel_set.filter(matched_transaction__isnull=True, ignored=False).exists()
    reconciliation.status = (
        BankReconciliationModel.STATUS_REVIEW if unmatched else BankReconciliationModel.STATUS_RECONCILED
    )
    if not unmatched:
        reconciliation.reconciled_by = user_model
        reconciliation.reconciled_at = timezone.now()
        statement_model.status = BankStatementModel.STATUS_RECONCILED
        statement_model.save(update_fields=['status', 'updated'])
    reconciliation.save(update_fields=['status', 'reconciled_by', 'reconciled_at', 'updated'])
    create_audit_event(
        entity_model=statement_model.entity_model,
        action=AuditEventModel.ACTION_STATE,
        actor=user_model,
        target=statement_model,
        after={'reconciliation_status': reconciliation.status},
    )
    return reconciliation


def match_bank_statement_line(*, statement_line: BankStatementLineModel, transaction_model, user_model=None) -> BankStatementLineModel:
    if statement_line.entity_model_id != transaction_model.journal_entry.ledger.entity_id:
        raise EnterpriseModelValidationError('Cannot match a statement line to a transaction from another entity.')
    before = {
        'matched_transaction': str(statement_line.matched_transaction_id) if statement_line.matched_transaction_id else '',
        'reconciled': bool(getattr(transaction_model, 'reconciled', False)),
    }
    statement_line.matched_transaction = transaction_model
    statement_line.save(update_fields=['matched_transaction', 'updated'])
    transaction_model.__class__.objects.filter(pk=transaction_model.pk).update(
        reconciled=True,
        updated=timezone.now(),
    )
    transaction_model.reconciled = True
    create_audit_event(
        entity_model=statement_line.entity_model,
        action=AuditEventModel.ACTION_STATE,
        actor=user_model,
        target=statement_line,
        before=before,
        after={
            'matched_transaction': str(transaction_model.pk),
            'reconciled': True,
        },
    )
    return statement_line


def calculate_tax(*, entity_model, target, tax_code, taxable_amount: Decimal, inclusive: bool = False, on_date=None):
    on_date = on_date or timezone.localdate()
    rate_model = TaxRateModel.objects.for_entity(entity_model).filter(
        tax_code=tax_code,
        effective_date__lte=on_date,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=on_date),
    ).order_by('-effective_date').first()
    if not rate_model:
        raise EnterpriseModelValidationError('No active tax rate found for tax code.')
    rate = rate_model.rate
    if inclusive:
        tax_amount = taxable_amount - (taxable_amount / (Decimal('1.00') + rate))
    else:
        tax_amount = taxable_amount * rate
    tax_amount = tax_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    kwargs = _target_kwargs(target)
    kwargs.pop('object_repr', None)
    return TaxLineModel.objects.create(
        entity_model=entity_model,
        tax_code=tax_code,
        tax_rate=rate_model,
        taxable_amount=taxable_amount,
        tax_amount=tax_amount,
        inclusive=inclusive,
        **kwargs,
    )


def allocate_payment(*, payment: PaymentModel, target, amount: Decimal, write_off_amount=Decimal('0.00')) -> PaymentAllocationModel:
    allocated = payment.paymentallocationmodel_set.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    if allocated + amount > payment.amount:
        raise EnterpriseModelValidationError('Cannot allocate more than the payment amount.')
    kwargs = _target_kwargs(target)
    kwargs.pop('object_repr', None)
    allocation = PaymentAllocationModel.objects.create(
        entity_model=payment.entity_model,
        payment=payment,
        amount=amount,
        write_off_amount=write_off_amount,
        **kwargs,
    )
    payment.unapplied_amount = payment.amount - allocated - amount
    payment.save(update_fields=['unapplied_amount', 'updated'])
    return allocation


def create_payment(
    *,
    entity_model,
    direction: str,
    payment_date,
    amount: Decimal,
    user_model=None,
    currency=None,
    exchange_rate: Decimal | None = None,
    bank_account=None,
    customer=None,
    vendor=None,
    reference: str = '',
) -> PaymentModel:
    require_entity_role(
        user_model,
        entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
        EntityRoleModel.ROLE_ACCOUNTANT,
    )
    assert_period_open(entity_model, payment_date)
    base_amount = calculate_base_amount(
        entity_model=entity_model,
        amount=amount,
        currency=currency,
        exchange_rate=exchange_rate,
    )
    payment = PaymentModel.objects.create(
        entity_model=entity_model,
        direction=direction,
        payment_date=payment_date,
        amount=amount,
        unapplied_amount=amount,
        base_amount=base_amount,
        currency=currency,
        bank_account=bank_account,
        customer=customer,
        vendor=vendor,
        reference=reference,
    )
    create_audit_event(
        entity_model=entity_model,
        action=AuditEventModel.ACTION_CREATE,
        actor=user_model,
        target=payment,
        after={'amount': str(amount), 'direction': direction, 'status': payment.status},
    )
    enqueue_webhook_event(entity_model=entity_model, event_type='payment.created', payload={'payment': str(payment.uuid)})
    return payment


def approve_payment(*, payment: PaymentModel, user_model) -> PaymentModel:
    require_entity_role(
        user_model,
        payment.entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
        EntityRoleModel.ROLE_APPROVER,
    )
    before = {'status': payment.status}
    payment.status = PaymentModel.STATUS_APPROVED
    payment.save(update_fields=['status', 'updated'])
    create_audit_event(
        entity_model=payment.entity_model,
        action=AuditEventModel.ACTION_APPROVE,
        actor=user_model,
        target=payment,
        before=before,
        after={'status': payment.status},
    )
    return payment


def post_payment(*, payment: PaymentModel, user_model=None) -> PaymentModel:
    require_entity_role(
        user_model,
        payment.entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
        EntityRoleModel.ROLE_ACCOUNTANT,
    )
    assert_period_open(payment.entity_model, payment.payment_date)
    if payment.status not in [PaymentModel.STATUS_APPROVED, PaymentModel.STATUS_DRAFT]:
        raise EnterpriseModelValidationError('Only draft or approved payments can be posted.')
    before = {'status': payment.status}
    payment.status = PaymentModel.STATUS_POSTED
    payment.save(update_fields=['status', 'updated'])
    create_audit_event(
        entity_model=payment.entity_model,
        action=AuditEventModel.ACTION_POST,
        actor=user_model,
        target=payment,
        before=before,
        after={'status': payment.status},
    )
    enqueue_webhook_event(entity_model=payment.entity_model, event_type='payment.posted', payload={'payment': str(payment.uuid)})
    return payment


def reverse_payment(*, payment: PaymentModel, user_model=None, reason: str = '') -> PaymentModel:
    require_entity_role(
        user_model,
        payment.entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
        EntityRoleModel.ROLE_ACCOUNTANT,
    )
    assert_period_open(payment.entity_model, payment.payment_date)
    before = {'status': payment.status, 'unapplied_amount': str(payment.unapplied_amount)}
    payment.paymentallocationmodel_set.all().delete()
    payment.unapplied_amount = payment.amount
    payment.status = PaymentModel.STATUS_VOID
    payment.save(update_fields=['unapplied_amount', 'status', 'updated'])
    create_audit_event(
        entity_model=payment.entity_model,
        action=AuditEventModel.ACTION_STATE,
        actor=user_model,
        target=payment,
        before=before,
        after={'status': payment.status, 'reason': reason},
    )
    return payment


def unallocate_payment(*, allocation: PaymentAllocationModel, user_model=None) -> PaymentModel:
    payment = allocation.payment
    require_entity_role(
        user_model,
        payment.entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
        EntityRoleModel.ROLE_ACCOUNTANT,
    )
    amount = allocation.amount
    allocation.delete()
    allocated = payment.paymentallocationmodel_set.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    payment.unapplied_amount = payment.amount - allocated
    payment.save(update_fields=['unapplied_amount', 'updated'])
    create_audit_event(
        entity_model=payment.entity_model,
        action=AuditEventModel.ACTION_STATE,
        actor=user_model,
        target=payment,
        after={'unallocated_amount': str(amount), 'unapplied_amount': str(payment.unapplied_amount)},
    )
    return payment


def apply_payment_to_document(*, payment: PaymentModel, target, amount: Decimal, user_model=None, write_off_amount=Decimal('0.00')):
    entity_model = get_target_entity(target)
    if entity_model.pk != payment.entity_model_id:
        raise EnterpriseModelValidationError('Cannot allocate a payment across entities.')
    allocation = allocate_payment(payment=payment, target=target, amount=amount, write_off_amount=write_off_amount)
    if hasattr(target, 'make_payment'):
        target.make_payment(payment_amount=amount + write_off_amount, payment_date=payment.payment_date, commit=True)
    create_audit_event(
        entity_model=payment.entity_model,
        action=AuditEventModel.ACTION_STATE,
        actor=user_model,
        target=target,
        after={
            'payment': str(payment.uuid),
            'amount': str(amount),
            'write_off_amount': str(write_off_amount),
        },
    )
    return allocation


def create_credit_note(*, entity_model, customer, amount: Decimal, note_date, user_model=None, invoice=None, note_number: str = '') -> CreditNoteModel:
    require_entity_role(user_model, entity_model, EntityRoleModel.ROLE_OWNER, EntityRoleModel.ROLE_FINANCE_ADMIN, EntityRoleModel.ROLE_ACCOUNTANT)
    credit_note = CreditNoteModel.objects.create(
        entity_model=entity_model,
        customer=customer,
        invoice=invoice,
        amount=amount,
        unapplied_amount=amount,
        note_date=note_date,
        note_number=note_number,
    )
    create_audit_event(entity_model=entity_model, action=AuditEventModel.ACTION_CREATE, actor=user_model, target=credit_note, after={'amount': str(amount)})
    return credit_note


def create_debit_note(*, entity_model, vendor, amount: Decimal, note_date, user_model=None, bill=None, note_number: str = '') -> DebitNoteModel:
    require_entity_role(user_model, entity_model, EntityRoleModel.ROLE_OWNER, EntityRoleModel.ROLE_FINANCE_ADMIN, EntityRoleModel.ROLE_ACCOUNTANT)
    debit_note = DebitNoteModel.objects.create(
        entity_model=entity_model,
        vendor=vendor,
        bill=bill,
        amount=amount,
        unapplied_amount=amount,
        note_date=note_date,
        note_number=note_number,
    )
    create_audit_event(entity_model=entity_model, action=AuditEventModel.ACTION_CREATE, actor=user_model, target=debit_note, after={'amount': str(amount)})
    return debit_note


def detect_duplicate_bill(*, bill_model):
    vendor = getattr(bill_model, 'vendor', None)
    if vendor is None:
        return bill_model.__class__.objects.none()
    qs = bill_model.__class__.objects.filter(
        vendor=vendor,
        amount_due=getattr(bill_model, 'amount_due', None),
    ).exclude(pk=bill_model.pk)
    bill_number = getattr(bill_model, 'bill_number', '')
    if bill_number:
        qs = qs.filter(bill_number=bill_number)
    bill_date = getattr(bill_model, 'date_draft', None) or getattr(bill_model, 'date_due', None)
    if bill_date:
        qs = qs.filter(Q(date_draft=bill_date) | Q(date_due=bill_date))
    return qs


def get_exchange_rate(*, entity_model, from_currency, to_currency, on_date=None) -> ExchangeRateModel:
    on_date = on_date or timezone.localdate()
    if from_currency == to_currency:
        return ExchangeRateModel(
            entity_model=entity_model,
            from_currency=from_currency,
            to_currency=to_currency,
            rate=Decimal('1.00'),
            rate_date=on_date,
        )
    rate_model = ExchangeRateModel.objects.for_entity(entity_model).filter(
        from_currency=from_currency,
        to_currency=to_currency,
        rate_date__lte=on_date,
    ).order_by('-rate_date').first()
    if not rate_model:
        raise EnterpriseModelValidationError('No exchange rate found.')
    return rate_model


def calculate_base_amount(*, entity_model, amount: Decimal, currency=None, exchange_rate: Decimal | None = None, on_date=None) -> Decimal:
    base_currency = getattr(entity_model, 'base_currency', None)
    if not currency or not base_currency or currency == base_currency:
        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    rate = exchange_rate
    if rate is None:
        rate = get_exchange_rate(
            entity_model=entity_model,
            from_currency=currency,
            to_currency=base_currency,
            on_date=on_date,
        ).rate
    return (amount * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def apply_document_currency(*, target, entity_model=None, currency=None, exchange_rate: Decimal | None = None, amount_field: str = 'amount_due'):
    entity_model = entity_model or get_target_entity(target)
    currency = currency or getattr(target, 'currency', None)
    if currency and hasattr(target, 'currency'):
        target.currency = currency
    if exchange_rate is not None and hasattr(target, 'exchange_rate'):
        target.exchange_rate = exchange_rate
    amount = getattr(target, amount_field, None)
    if amount is None and hasattr(target, 'po_amount'):
        amount_field = 'po_amount'
        amount = getattr(target, amount_field)
    if amount is None:
        raise EnterpriseModelValidationError('Target does not expose a supported amount field.')
    base_amount = calculate_base_amount(
        entity_model=entity_model,
        amount=amount,
        currency=currency,
        exchange_rate=exchange_rate or getattr(target, 'exchange_rate', None),
    )
    for base_field in ('base_amount_due', 'base_po_amount', 'base_amount'):
        if hasattr(target, base_field):
            setattr(target, base_field, base_amount)
            break
    return target


def calculate_document_taxes(*, entity_model, target, tax_code, inclusive: bool = False, on_date=None) -> list[TaxLineModel]:
    itemtxs = getattr(target, 'itemtransactionmodel_set', None)
    if itemtxs is None:
        amount = getattr(target, 'amount_due', None) or getattr(target, 'po_amount', None)
        return [calculate_tax(
            entity_model=entity_model,
            target=target,
            tax_code=tax_code,
            taxable_amount=amount,
            inclusive=inclusive,
            on_date=on_date,
        )]
    tax_lines = []
    for itemtx in itemtxs.all():
        amount = getattr(itemtx, 'total_amount', None) or getattr(itemtx, 'po_total_amount', None)
        if amount:
            tax_lines.append(calculate_tax(
                entity_model=entity_model,
                target=itemtx,
                tax_code=tax_code,
                taxable_amount=amount,
                inclusive=inclusive,
                on_date=on_date,
            ))
    return tax_lines


def get_realized_fx_gain_loss(*, settlement_amount: Decimal, settlement_rate: Decimal, document_amount: Decimal, document_rate: Decimal) -> Decimal:
    settlement_base = settlement_amount * settlement_rate
    document_base = document_amount * document_rate
    return (settlement_base - document_base).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def revalue_currency_balances(*, entity_model, from_currency, to_currency, on_date=None):
    rate_model = get_exchange_rate(
        entity_model=entity_model,
        from_currency=from_currency,
        to_currency=to_currency,
        on_date=on_date,
    )
    open_items = []
    for model_name, amount_field in [('InvoiceModel', 'amount_receivable'), ('BillModel', 'amount_receivable')]:
        model_cls = apps.get_model('django_ledger', model_name)
        for obj in model_cls.objects.for_entity(entity_model=entity_model).filter(currency=from_currency):
            amount = getattr(obj, amount_field, None) or Decimal('0.00')
            current_base = getattr(obj, 'base_amount_due', None) or Decimal('0.00')
            revalued_base = (amount * rate_model.rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            delta = revalued_base - current_base
            if delta:
                open_items.append({
                    'target': obj,
                    'amount': amount,
                    'current_base': current_base,
                    'revalued_base': revalued_base,
                    'gain_loss': delta,
                })
    return {
        'entity_model': entity_model,
        'from_currency': from_currency,
        'to_currency': to_currency,
        'rate': rate_model.rate,
        'entries': open_items,
    }


def create_straight_line_depreciation_schedule(*, fixed_asset: FixedAssetModel) -> list[DepreciationScheduleModel]:
    method = fixed_asset.depreciation_method
    if method.method != method.METHOD_STRAIGHT_LINE:
        raise EnterpriseModelValidationError('Only straight-line depreciation is supported by this scheduler.')
    depreciable_amount = fixed_asset.acquisition_cost - fixed_asset.salvage_value
    if depreciable_amount < Decimal('0.00'):
        raise EnterpriseModelValidationError('Salvage value cannot exceed acquisition cost.')
    monthly_amount = (depreciable_amount / Decimal(method.useful_life_months)).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP,
    )
    periods = AccountingPeriodModel.objects.for_entity(fixed_asset.entity_model).filter(
        end_date__gte=fixed_asset.acquisition_date,
    ).order_by('start_date')[:method.useful_life_months]
    schedules = []
    for period in periods:
        schedule, _ = DepreciationScheduleModel.objects.get_or_create(
            entity_model=fixed_asset.entity_model,
            fixed_asset=fixed_asset,
            period=period,
            defaults={'depreciation_amount': monthly_amount},
        )
        schedules.append(schedule)
    return schedules


def assign_dimension(*, entity_model, target, dimension_value: DimensionValueModel, weight=Decimal('1.00')) -> DimensionAssignmentModel:
    if dimension_value.entity_model_id != entity_model.pk:
        raise EnterpriseModelValidationError('Dimension value belongs to a different entity.')
    kwargs = _target_kwargs(target)
    kwargs.pop('object_repr', None)
    assignment, _ = DimensionAssignmentModel.objects.update_or_create(
        entity_model=entity_model,
        dimension_value=dimension_value,
        content_type=kwargs['content_type'],
        object_id=kwargs['object_id'],
        defaults={'weight': weight},
    )
    return assignment


def approve_budget_version(*, budget_version: BudgetVersionModel, user_model) -> BudgetVersionModel:
    require_entity_role(
        user_model,
        budget_version.entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
        EntityRoleModel.ROLE_APPROVER,
    )
    before = {'status': budget_version.status}
    budget_version.status = 'approved'
    budget_version.approved_by = user_model
    budget_version.save(update_fields=['status', 'approved_by', 'updated'])
    create_audit_event(
        entity_model=budget_version.entity_model,
        action=AuditEventModel.ACTION_APPROVE,
        actor=user_model,
        target=budget_version,
        before=before,
        after={'status': budget_version.status},
    )
    return budget_version


def calculate_allocation_rule(*, allocation_rule: AllocationRuleModel, amount: Decimal) -> list[dict]:
    lines = []
    allocated_total = Decimal('0.00')
    rule_lines = list(allocation_rule.allocationrulelinemodel_set.all().order_by('created'))
    for index, line in enumerate(rule_lines):
        if index == len(rule_lines) - 1:
            line_amount = amount - allocated_total
        else:
            line_amount = (amount * line.percentage).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            allocated_total += line_amount
        lines.append({
            'target_account': line.target_account,
            'dimension_value': line.dimension_value,
            'percentage': line.percentage,
            'amount': line_amount,
        })
    return lines


def mark_depreciation_posted(*, schedule: DepreciationScheduleModel, journal_entry=None, user_model=None) -> DepreciationScheduleModel:
    assert_period_open(schedule.entity_model, schedule.period.end_date)
    before = {'posted': schedule.posted}
    schedule.posted = True
    if journal_entry is not None:
        schedule.journal_entry = journal_entry
    schedule.save(update_fields=['posted', 'journal_entry', 'updated'])
    create_audit_event(
        entity_model=schedule.entity_model,
        action=AuditEventModel.ACTION_POST,
        actor=user_model,
        target=schedule.fixed_asset,
        before=before,
        after={'posted': True, 'depreciation_amount': str(schedule.depreciation_amount)},
    )
    return schedule


def dispose_fixed_asset(*, fixed_asset: FixedAssetModel, disposal_date, proceeds=Decimal('0.00'), user_model=None, journal_entry=None, notes: str = '') -> AssetDisposalModel:
    require_entity_role(user_model, fixed_asset.entity_model, EntityRoleModel.ROLE_OWNER, EntityRoleModel.ROLE_FINANCE_ADMIN, EntityRoleModel.ROLE_ACCOUNTANT)
    assert_period_open(fixed_asset.entity_model, disposal_date)
    disposal = AssetDisposalModel.objects.create(
        entity_model=fixed_asset.entity_model,
        fixed_asset=fixed_asset,
        disposal_date=disposal_date,
        proceeds=proceeds,
        journal_entry=journal_entry,
        notes=notes,
    )
    before = {'status': fixed_asset.status}
    fixed_asset.status = FixedAssetModel.STATUS_DISPOSED
    fixed_asset.save(update_fields=['status', 'updated'])
    create_audit_event(
        entity_model=fixed_asset.entity_model,
        action=AuditEventModel.ACTION_STATE,
        actor=user_model,
        target=fixed_asset,
        before=before,
        after={'status': fixed_asset.status, 'proceeds': str(proceeds)},
    )
    return disposal


def attach_document(*, entity_model, target, file_obj, uploaded_by=None, original_filename: str = '') -> DocumentAttachmentModel:
    checksum = ''
    if file_obj:
        position = file_obj.tell() if hasattr(file_obj, 'tell') else None
        checksum = hashlib.sha256(file_obj.read()).hexdigest()
        if position is not None:
            file_obj.seek(position)
    kwargs = _target_kwargs(target)
    kwargs.pop('object_repr', None)
    document = DocumentAttachmentModel.objects.create(
        entity_model=entity_model,
        uploaded_by=uploaded_by,
        file=file_obj,
        original_filename=original_filename or getattr(file_obj, 'name', ''),
        checksum=checksum,
        **kwargs,
    )
    create_audit_event(
        entity_model=entity_model,
        action=AuditEventModel.ACTION_CREATE,
        actor=uploaded_by,
        target=target,
        after={'attachment': str(document.uuid), 'checksum': checksum},
    )
    return document


def export_rows_to_csv(rows: Iterable[dict], fieldnames: list[str]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def export_queryset_to_csv(*, entity_model, queryset, fieldnames: list[str], user_model=None) -> str:
    require_entity_role(
        user_model,
        entity_model,
        EntityRoleModel.ROLE_OWNER,
        EntityRoleModel.ROLE_FINANCE_ADMIN,
        EntityRoleModel.ROLE_ACCOUNTANT,
        EntityRoleModel.ROLE_AUDITOR,
        EntityRoleModel.ROLE_INTEGRATION,
    )
    csv_text = export_rows_to_csv(queryset.values(*fieldnames), fieldnames)
    create_audit_event(
        entity_model=entity_model,
        action=AuditEventModel.ACTION_EXPORT,
        actor=user_model,
        after={'fieldnames': fieldnames, 'row_count': queryset.count()},
    )
    return csv_text


def enqueue_webhook_event(*, entity_model, event_type: str, payload: dict) -> list[WebhookDeliveryModel]:
    deliveries = []
    endpoints = WebhookEndpointModel.objects.for_entity(entity_model).active()
    for endpoint in endpoints:
        event_types = endpoint.event_types or []
        if event_types and event_type not in event_types:
            continue
        deliveries.append(WebhookDeliveryModel.objects.create(
            entity_model=entity_model,
            endpoint=endpoint,
            event_type=event_type,
            payload=payload,
        ))
    return deliveries


def record_webhook_delivery_attempt(*, delivery: WebhookDeliveryModel, status_code=None, response_body: str = '') -> WebhookDeliveryModel:
    delivery.status_code = status_code
    delivery.response_body = response_body
    delivery.delivered = bool(status_code and 200 <= status_code < 300)
    delivery.attempt_count += 1
    delivery.save(update_fields=['status_code', 'response_body', 'delivered', 'attempt_count', 'updated'])
    return delivery
