"""
Quarterly VAT and turnover reports for German tax regimes.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from django.db.models import Sum

from django_ledger.io.roles import GROUP_INCOME
from django_ledger.models.utils import lazy_loader
from django_ledger_extensions.models import EntityTaxProfile

from django_ledger_countries.de.roles import ASSET_CA_VAT_RECEIVABLE, LIABILITY_CL_VAT_PAYABLE
from django_ledger_countries.settings import get_ledger_setting


@dataclass
class VatQuarterlyReport:
    entity_slug: str
    tax_regime: str
    year: int
    quarter: int
    period_start: date
    period_end: date
    input_vat: Decimal = Decimal('0')
    output_vat: Decimal = Decimal('0')
    net_vat_payable: Decimal = Decimal('0')
    quarter_turnover: Decimal = Decimal('0')
    ytd_turnover: Decimal = Decimal('0')
    prior_year_turnover: Decimal = Decimal('0')
    filing_summary: str = ''
    action_items: List[str] = field(default_factory=list)


def quarter_date_range(year: int, quarter: int) -> Tuple[date, date]:
    if quarter not in (1, 2, 3, 4):
        raise ValueError('quarter must be 1–4')
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    start = date(year, start_month, 1)
    end = date(year, end_month, calendar.monthrange(year, end_month)[1])
    return start, end


def current_quarter(reference: Optional[date] = None) -> Tuple[int, int]:
    reference = reference or date.today()
    return reference.year, ((reference.month - 1) // 3) + 1


def _sum_amount(qs, *, tx_type: str) -> Decimal:
    total = qs.filter(tx_type=tx_type).aggregate(total=Sum('amount'))['total']
    return Decimal(str(total or 0))


def _net_turnover(qs) -> Decimal:
    credits = _sum_amount(qs, tx_type='credit')
    debits = _sum_amount(qs, tx_type='debit')
    return credits - debits


def _posted_transactions(entity, start: date, end: date):
    TransactionModel = lazy_loader.get_txs_model()
    return (
        TransactionModel.objects.for_entity(entity)
        .posted()
        .from_date(start)
        .to_date(end)
    )


def _kleinunternehmer_limits() -> Tuple[Decimal, Decimal]:
    prior = Decimal(str(get_ledger_setting('KLEINUNTERNEHMER_PRIOR_YEAR_LIMIT')))
    current = Decimal(str(get_ledger_setting('KLEINUNTERNEHMER_CURRENT_YEAR_LIMIT')))
    return prior, current


def build_vat_quarterly_report(entity, year: int, quarter: int) -> VatQuarterlyReport:
    period_start, period_end = quarter_date_range(year, quarter)
    ytd_start = date(year, 1, 1)
    prior_year_start = date(year - 1, 1, 1)
    prior_year_end = date(year - 1, 12, 31)

    try:
        tax_regime = entity.tax_profile.tax_regime
    except Exception:
        tax_regime = EntityTaxProfile.TaxRegime.EXEMPT

    quarter_qs = _posted_transactions(entity, period_start, period_end)
    ytd_qs = _posted_transactions(entity, ytd_start, period_end)
    prior_qs = _posted_transactions(entity, prior_year_start, prior_year_end)

    report = VatQuarterlyReport(
        entity_slug=entity.slug,
        tax_regime=tax_regime,
        year=year,
        quarter=quarter,
        period_start=period_start,
        period_end=period_end,
        quarter_turnover=_net_turnover(quarter_qs.filter(account__role__in=GROUP_INCOME)),
        ytd_turnover=_net_turnover(ytd_qs.filter(account__role__in=GROUP_INCOME)),
        prior_year_turnover=_net_turnover(prior_qs.filter(account__role__in=GROUP_INCOME)),
    )

    if tax_regime == EntityTaxProfile.TaxRegime.STANDARD:
        vat_qs = quarter_qs.filter(
            account__role__in=[ASSET_CA_VAT_RECEIVABLE, LIABILITY_CL_VAT_PAYABLE]
        )
        report.input_vat = _sum_amount(
            vat_qs.filter(account__role=ASSET_CA_VAT_RECEIVABLE),
            tx_type='debit',
        )
        report.output_vat = _sum_amount(
            vat_qs.filter(account__role=LIABILITY_CL_VAT_PAYABLE),
            tx_type='credit',
        )
        report.net_vat_payable = report.output_vat - report.input_vat
        report.filing_summary = (
            f'USt-Voranmeldung (ELSTER): expected payment ≈ {report.net_vat_payable:.2f} € '
            f'(Umsatzsteuer {report.output_vat:.2f} € − Vorsteuer {report.input_vat:.2f} €). '
            f'File by the 10th of the month after the quarter ends if you file quarterly.'
        )
        if report.net_vat_payable < 0:
            report.action_items.append(
                f'Expected refund/credit of {abs(report.net_vat_payable):.2f} € '
                f'(Vorsteuer exceeds Umsatzsteuer this quarter).'
            )
    elif tax_regime == EntityTaxProfile.TaxRegime.SMALL_BUSINESS:
        prior_limit, current_limit = _kleinunternehmer_limits()
        report.filing_summary = (
            'Kleinunternehmer (§ 19 UStG): no Umsatzsteuervoranmeldung and no VAT charged. '
            f'Quarter turnover {report.quarter_turnover:.2f} €; '
            f'year-to-date {report.ytd_turnover:.2f} €.'
        )
        if report.prior_year_turnover > prior_limit:
            report.action_items.append(
                f'Prior-year turnover {report.prior_year_turnover:.2f} € exceeds '
                f'the § 19 threshold of {prior_limit:.2f} € — confirm Kleinunternehmer status with your Steuerberater.'
            )
        if report.ytd_turnover > current_limit:
            report.action_items.append(
                f'Year-to-date turnover {report.ytd_turnover:.2f} € exceeds '
                f'the current-year expectation limit of {current_limit:.2f} € — you may lose Kleinunternehmer status.'
            )
    else:
        report.filing_summary = (
            'Tax-exempt school/training (§ 4 UStG): no VAT on exempt course fees and typically '
            'no USt-Voranmeldung for those supplies. '
            f'Quarter turnover {report.quarter_turnover:.2f} €; '
            f'year-to-date {report.ytd_turnover:.2f} € (for your records).'
        )

    return report


def format_vat_quarterly_report(report: VatQuarterlyReport) -> str:
    lines = [
        f'VAT quarterly report — {report.entity_slug}',
        f'Regime: {report.tax_regime}',
        f'Period: Q{report.quarter} {report.year} ({report.period_start.isoformat()} – {report.period_end.isoformat()})',
        '',
    ]
    if report.tax_regime == EntityTaxProfile.TaxRegime.STANDARD:
        lines.extend(
            [
                f'  Vorsteuer (input VAT):     {report.input_vat:>12.2f} €',
                f'  Umsatzsteuer (output VAT): {report.output_vat:>12.2f} €',
                f'  Expected payment (Zahllast): {report.net_vat_payable:>12.2f} €',
                '',
            ]
        )
    lines.extend(
        [
            f'  Quarter turnover:          {report.quarter_turnover:>12.2f} €',
            f'  Year-to-date turnover:     {report.ytd_turnover:>12.2f} €',
        ]
    )
    if report.tax_regime == EntityTaxProfile.TaxRegime.SMALL_BUSINESS:
        prior_limit, current_limit = _kleinunternehmer_limits()
        lines.extend(
            [
                f'  Prior-year turnover:       {report.prior_year_turnover:>12.2f} €  (limit {prior_limit:.0f} €)',
                f'  YTD vs current-year limit: {report.ytd_turnover:>12.2f} €  (limit {current_limit:.0f} €)',
            ]
        )
    lines.extend(['', report.filing_summary])
    if report.action_items:
        lines.append('')
        lines.append('Action items:')
        for item in report.action_items:
            lines.append(f'  • {item}')
    return '\n'.join(lines)
