"""
Service-layer APIs for medium-company accounting workflows.
"""
from __future__ import annotations

import csv
import hashlib
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
from typing import Iterable, Optional

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from django_ledger.models.enterprise import (
    AccountingPeriodModel,
    ApprovalPolicyModel,
    ApprovalRequestModel,
    AuditEventModel,
    BankReconciliationModel,
    BankStatementLineModel,
    BankStatementModel,
    DepreciationScheduleModel,
    DocumentAttachmentModel,
    EnterpriseModelValidationError,
    ExchangeRateModel,
    FixedAssetModel,
    PaymentAllocationModel,
    PaymentModel,
    TaxLineModel,
    TaxRateModel,
)


def _target_kwargs(target):
    if not target:
        return {}
    return {
        'content_type': ContentType.objects.get_for_model(target, for_concrete_model=False),
        'object_id': str(target.pk),
        'object_repr': str(target),
    }


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


def request_approval(*, entity_model, target, requested_by=None, amount=None, reason: str = '') -> ApprovalRequestModel:
    target_type = target.__class__.__name__.lower()
    policies = ApprovalPolicyModel.objects.for_entity(entity_model).active().filter(
        document_type__in=[target_type, ApprovalPolicyModel.DOCUMENT_ALL],
    )
    if amount is not None:
        policies = policies.filter(
            Q(min_amount__isnull=True) | Q(min_amount__lte=amount),
            Q(max_amount__isnull=True) | Q(max_amount__gte=amount),
        )
    policy = policies.order_by('-min_amount').first()
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


def revalue_currency_balances(*, entity_model, from_currency, to_currency, on_date=None):
    rate_model = get_exchange_rate(
        entity_model=entity_model,
        from_currency=from_currency,
        to_currency=to_currency,
        on_date=on_date,
    )
    return {
        'entity_model': entity_model,
        'from_currency': from_currency,
        'to_currency': to_currency,
        'rate': rate_model.rate,
        'entries': [],
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


def attach_document(*, entity_model, target, file_obj, uploaded_by=None, original_filename: str = '') -> DocumentAttachmentModel:
    checksum = ''
    if file_obj:
        position = file_obj.tell() if hasattr(file_obj, 'tell') else None
        checksum = hashlib.sha256(file_obj.read()).hexdigest()
        if position is not None:
            file_obj.seek(position)
    kwargs = _target_kwargs(target)
    kwargs.pop('object_repr', None)
    return DocumentAttachmentModel.objects.create(
        entity_model=entity_model,
        uploaded_by=uploaded_by,
        file=file_obj,
        original_filename=original_filename or getattr(file_obj, 'name', ''),
        checksum=checksum,
        **kwargs,
    )


def export_rows_to_csv(rows: Iterable[dict], fieldnames: list[str]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()
