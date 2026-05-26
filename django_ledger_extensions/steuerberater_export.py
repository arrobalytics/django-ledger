"""
Steuerberater handoff bundle — posted JEs, Beleg index, VAT summary.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Optional, Union

from django.contrib.contenttypes.models import ContentType

from django_ledger.models.utils import lazy_loader

from django_ledger_extensions.models import EntityTaxProfile, SupportingDocumentModel

try:
    from django_ledger_countries.de.vat.reporting import build_vat_quarterly_report, current_quarter
except ImportError:
    build_vat_quarterly_report = None
    current_quarter = None


def _period_bounds(year: int, month: Optional[int] = None) -> tuple[date, date]:
    if month is None:
        return date(year, 1, 1), date(year, 12, 31)
    if month == 12:
        return date(year, 12, 1), date(year, 12, 31)
    return date(year, month, 1), date(year, month + 1, 1) - timedelta(days=1)


def _serialize_decimal(value) -> str:
    if isinstance(value, Decimal):
        return str(value)
    return value


def build_steuerberater_bundle(
    entity,
    *,
    year: int,
    month: Optional[int] = None,
) -> Dict[str, Any]:
    start, end = _period_bounds(year, month)
    TransactionModel = lazy_loader.get_txs_model()
    JournalEntryModel = lazy_loader.get_journal_entry_model()

    txs = (
        TransactionModel.objects.for_entity(entity)
        .posted()
        .from_date(start)
        .to_date(end)
        .select_related('account', 'journal_entry', 'journal_entry__ledger')
        .order_by('journal_entry__timestamp', 'account__code')
    )

    journal_lines = []
    for tx in txs:
        journal_lines.append(
            {
                'date': tx.journal_entry.timestamp.date().isoformat(),
                'je_uuid': str(tx.journal_entry_id),
                'ledger': tx.journal_entry.ledger.name,
                'account_code': tx.account.code,
                'account_name': tx.account.name,
                'tx_type': tx.tx_type,
                'amount': _serialize_decimal(tx.amount),
                'description': tx.description or tx.journal_entry.description,
            }
        )

    je_uuids = {line['je_uuid'] for line in journal_lines}
    je_ct = ContentType.objects.get_for_model(JournalEntryModel)
    invoice_ct = ContentType.objects.get_for_model(lazy_loader.get_invoice_model())
    bill_ct = ContentType.objects.get_for_model(lazy_loader.get_bill_model())

    docs = SupportingDocumentModel.objects.filter(
        content_type__in=[je_ct, invoice_ct, bill_ct],
    ).order_by('created')

    beleg_index = []
    for doc in docs:
        target_id = str(doc.object_id)
        if doc.content_type == je_ct and target_id not in je_uuids:
            continue
        beleg_index.append(
            {
                'document_uuid': str(doc.uuid),
                'document_type': doc.document_type,
                'target_type': doc.content_type.model,
                'target_id': target_id,
                'description': doc.description,
                'checksum': doc.checksum,
                'file': doc.file.name,
            }
        )

    profile = getattr(entity, 'tax_profile', None)
    tax_regime = profile.tax_regime if profile else EntityTaxProfile.TaxRegime.EXEMPT

    bundle: Dict[str, Any] = {
        'entity': {
            'slug': entity.slug,
            'name': entity.name,
        },
        'period': {
            'year': year,
            'month': month,
            'start': start.isoformat(),
            'end': end.isoformat(),
        },
        'tax_regime': tax_regime,
        'journal_entry_count': len(je_uuids),
        'transaction_count': len(journal_lines),
        'journal_lines': journal_lines,
        'beleg_index': beleg_index,
    }

    if build_vat_quarterly_report and current_quarter:
        if month:
            quarter = ((month - 1) // 3) + 1
        else:
            quarter = 4
        try:
            vat_report = build_vat_quarterly_report(entity, year=year, quarter=quarter)
            bundle['vat_summary'] = {
                'quarter': quarter,
                'input_vat': _serialize_decimal(vat_report.input_vat),
                'output_vat': _serialize_decimal(vat_report.output_vat),
                'net_vat_payable': _serialize_decimal(vat_report.net_vat_payable),
                'quarter_turnover': _serialize_decimal(vat_report.quarter_turnover),
                'ytd_turnover': _serialize_decimal(vat_report.ytd_turnover),
                'filing_summary': vat_report.filing_summary,
                'action_items': vat_report.action_items,
            }
        except Exception:
            bundle['vat_summary'] = None

    return bundle


def bundle_to_csv(journal_lines: list) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=['date', 'je_uuid', 'ledger', 'account_code', 'account_name', 'tx_type', 'amount', 'description'],
    )
    writer.writeheader()
    writer.writerows(journal_lines)
    return buffer.getvalue()


def write_steuerberater_bundle(
    entity,
    output_dir: Union[str, Path],
    *,
    year: int,
    month: Optional[int] = None,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = build_steuerberater_bundle(entity, year=year, month=month)

    suffix = f'{year}' if month is None else f'{year}-{month:02d}'
    json_path = output_dir / f'steuerberater-{entity.slug}-{suffix}.json'
    csv_path = output_dir / f'journal-{entity.slug}-{suffix}.csv'

    json_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding='utf-8')
    csv_path.write_text(bundle_to_csv(bundle['journal_lines']), encoding='utf-8')
    return json_path
