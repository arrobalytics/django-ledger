"""
Monthly accounting health check for German entities.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from django_ledger.models.utils import lazy_loader

from django_ledger_extensions.models import DocumentInboxItem, ExternalPaymentRecord
from django_ledger_extensions.settings import get_extension_setting


@dataclass
class HealthCheckItem:
    code: str
    severity: str
    message: str
    count: int = 0
    samples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AccountingHealthReport:
    entity_slug: str
    checked_at: date
    items: List[HealthCheckItem] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return sum(i.count for i in self.items if i.severity in ('warning', 'error'))

    def to_dict(self) -> dict:
        return {
            'entity_slug': self.entity_slug,
            'checked_at': self.checked_at.isoformat(),
            'issue_count': self.issue_count,
            'items': [asdict(i) for i in self.items],
        }


def _sample_qs(qs, fields: List[str], limit: int = 5) -> List[Dict[str, Any]]:
    return [dict((f, getattr(obj, f)) for f in fields) for obj in qs[:limit]]


def build_accounting_health_report(entity, *, reference: Optional[date] = None) -> AccountingHealthReport:
    reference = reference or date.today()
    stale_days = int(get_extension_setting('HEALTH_CHECK_STALE_DRAFT_DAYS'))
    stale_cutoff = reference - timedelta(days=stale_days)

    report = AccountingHealthReport(entity_slug=entity.slug, checked_at=reference)
    InvoiceModel = lazy_loader.get_invoice_model()
    BillModel = lazy_loader.get_bill_model()
    StagedTransactionModel = lazy_loader.get_staged_txs_model()

    draft_invoices = InvoiceModel.objects.filter(
        ledger__entity=entity,
        invoice_status='draft',
    )
    draft_count = draft_invoices.count()
    if draft_count:
        report.items.append(
            HealthCheckItem(
                code='draft_invoices',
                severity='warning',
                message='Draft student invoices waiting for review/approve.',
                count=draft_count,
                samples=_sample_qs(
                    draft_invoices.order_by('-updated'),
                    ['uuid', 'invoice_number', 'amount_due', 'updated'],
                ),
            )
        )

    stale_drafts = draft_invoices.filter(updated__date__lte=stale_cutoff)
    stale_count = stale_drafts.count()
    if stale_count:
        report.items.append(
            HealthCheckItem(
                code='stale_draft_invoices',
                severity='warning',
                message=f'Draft invoices older than {stale_days} days.',
                count=stale_count,
                samples=_sample_qs(stale_drafts, ['uuid', 'invoice_number', 'updated']),
            )
        )

    unlinked_inbox = DocumentInboxItem.objects.filter(
        entity=entity,
        status=DocumentInboxItem.Status.UNLINKED,
    )
    inbox_count = unlinked_inbox.count()
    if inbox_count:
        report.items.append(
            HealthCheckItem(
                code='unlinked_beleg_inbox',
                severity='warning',
                message='Belege in inbox not yet linked to invoice/bill/JE.',
                count=inbox_count,
                samples=_sample_qs(
                    unlinked_inbox.order_by('-created'),
                    ['uuid', 'description', 'suggested_amount', 'created'],
                ),
            )
        )

    open_bills = BillModel.objects.filter(
        ledger__entity=entity,
        bill_status='approved',
    )
    open_bill_count = open_bills.count()
    if open_bill_count:
        report.items.append(
            HealthCheckItem(
                code='approved_unpaid_bills',
                severity='info',
                message='Approved bills not yet marked paid.',
                count=open_bill_count,
                samples=_sample_qs(open_bills, ['uuid', 'bill_number', 'amount_due']),
            )
        )

    unmatched_payments = ExternalPaymentRecord.objects.filter(
        entity=entity,
        record_type=ExternalPaymentRecord.RecordType.PAYMENT,
        staged_transaction__isnull=True,
        status=ExternalPaymentRecord.Status.INVOICE_DRAFT,
    )
    unmatched_count = unmatched_payments.count()
    if unmatched_count:
        report.items.append(
            HealthCheckItem(
                code='unmatched_bank_payments',
                severity='warning',
                message='Webapp payments not linked to bank import lines.',
                count=unmatched_count,
                samples=_sample_qs(
                    unmatched_payments.order_by('-paid_at'),
                    ['uuid', 'provider', 'external_id', 'amount', 'paid_at'],
                ),
            )
        )

    manual_refunds = ExternalPaymentRecord.objects.filter(
        entity=entity,
        record_type=ExternalPaymentRecord.RecordType.REFUND,
        status=ExternalPaymentRecord.Status.MANUAL_ACTION_REQUIRED,
    )
    manual_count = manual_refunds.count()
    if manual_count:
        report.items.append(
            HealthCheckItem(
                code='refunds_need_manual_action',
                severity='error',
                message='Refunds on paid invoices need manual void/credit in ledger UI.',
                count=manual_count,
                samples=_sample_qs(manual_refunds, ['uuid', 'external_id', 'error_message']),
            )
        )

    try:
        unimported_bank = (
            StagedTransactionModel.objects.for_entity(entity)
            .filter(transaction_model__isnull=True, matched_transaction_model__isnull=True)
            .count()
        )
    except Exception:
        unimported_bank = 0

    if unimported_bank:
        report.items.append(
            HealthCheckItem(
                code='unimported_bank_lines',
                severity='info',
                message='Bank import lines not yet committed to the ledger.',
                count=unimported_bank,
            )
        )

    if not report.items:
        report.items.append(
            HealthCheckItem(
                code='all_clear',
                severity='ok',
                message='No open accounting hygiene issues detected.',
                count=0,
            )
        )

    return report


def format_health_report(report: AccountingHealthReport) -> str:
    lines = [
        f'Accounting health — {report.entity_slug} ({report.checked_at.isoformat()})',
        '',
    ]
    for item in report.items:
        prefix = item.severity.upper()
        if item.count:
            lines.append(f'  [{prefix}] {item.message} ({item.count})')
        else:
            lines.append(f'  [{prefix}] {item.message}')
    lines.append('')
    lines.append(f'Total issues: {report.issue_count}')
    return '\n'.join(lines)
