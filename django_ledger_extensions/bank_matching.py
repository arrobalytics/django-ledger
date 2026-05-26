"""
Match imported external payments to bank import staged transactions.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import List, Optional

from django.db.models import Q

from django_ledger.models.utils import lazy_loader

from django_ledger_extensions.models import ExternalPaymentRecord
from django_ledger_extensions.settings import get_extension_setting


def _amount_tolerance() -> Decimal:
    return Decimal(str(get_extension_setting('BANK_MATCH_AMOUNT_TOLERANCE')))


def _day_tolerance() -> int:
    return int(get_extension_setting('BANK_MATCH_DAY_TOLERANCE'))


def suggest_staged_transaction_matches(
    record: ExternalPaymentRecord,
    *,
    limit: int = 10,
) -> List:
    if record.record_type != ExternalPaymentRecord.RecordType.PAYMENT:
        return []

    StagedTransactionModel = lazy_loader.get_staged_txs_model()
    tolerance = _amount_tolerance()
    day_tol = _day_tolerance()
    paid_date = record.paid_at.date()
    low = record.amount - tolerance
    high = record.amount + tolerance
    date_from = paid_date - timedelta(days=day_tol)
    date_to = paid_date + timedelta(days=day_tol)

    qs = (
        StagedTransactionModel.objects.for_entity(record.entity)
        .filter(
            transaction_model__isnull=True,
            date_posted__gte=date_from,
            date_posted__lte=date_to,
        )
        .filter(Q(amount__gte=low, amount__lte=high) | Q(amount_split__gte=low, amount_split__lte=high))
        .exclude(external_payment_records__isnull=False)
        .order_by('date_posted')[:limit]
    )
    return list(qs)


def link_external_payment_to_staged_transaction(
    record: ExternalPaymentRecord,
    staged_transaction,
    *,
    replace: bool = False,
) -> ExternalPaymentRecord:
    if record.entity_id != staged_transaction.import_job.ledger_model.entity_id:
        raise ValueError('Staged transaction belongs to a different entity.')
    if record.staged_transaction_id and not replace:
        raise ValueError('Payment already linked to a staged transaction.')
    record.staged_transaction = staged_transaction
    record.save(update_fields=['staged_transaction', 'updated'])
    return record


def auto_match_external_payments(
    entity,
    *,
    limit: Optional[int] = None,
) -> List[ExternalPaymentRecord]:
    """Link payments to the first unique staged-transaction match."""
    qs = ExternalPaymentRecord.objects.filter(
        entity=entity,
        record_type=ExternalPaymentRecord.RecordType.PAYMENT,
        staged_transaction__isnull=True,
        status=ExternalPaymentRecord.Status.INVOICE_DRAFT,
    ).order_by('paid_at')
    if limit:
        qs = qs[:limit]

    linked: List[ExternalPaymentRecord] = []
    for record in qs:
        matches = suggest_staged_transaction_matches(record, limit=2)
        if len(matches) == 1:
            link_external_payment_to_staged_transaction(record, matches[0])
            linked.append(record)
    return linked
