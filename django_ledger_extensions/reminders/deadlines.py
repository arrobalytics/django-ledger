"""
Compute due dates for accounting reminder rules.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterator, List, Optional, Tuple

from django_ledger_countries.de.vat.reporting import current_quarter, quarter_date_range

from django_ledger_extensions.models import AccountingReminderRule


@dataclass(frozen=True)
class ReminderDeadline:
    period_key: str
    due_date: date
    title: str
    body_lines: List[str]


def _safe_date(year: int, month: int, day: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def vat_quarterly_filing_deadline(year: int, quarter: int) -> date:
    """German quarterly USt-Voranmeldung — due 10th of the month after quarter end."""
    _, period_end = quarter_date_range(year, quarter)
    if period_end.month == 12:
        return date(period_end.year + 1, 1, 10)
    return _safe_date(period_end.year, period_end.month + 1, 10)


def monthly_bookkeeping_deadline(reference: date) -> date:
    """Internal close — 5th of the month following the period."""
    if reference.month == 12:
        return date(reference.year + 1, 1, 5)
    return _safe_date(reference.year, reference.month + 1, 5)


def year_end_handoff_deadline(year: int) -> date:
    """Reminder to send prior-year books to Steuerberater — default 31 January."""
    return date(year + 1, 1, 31)


def iter_deadlines_for_rule(
    rule: AccountingReminderRule,
    *,
    reference: Optional[date] = None,
    horizon_days: int = 120,
) -> Iterator[ReminderDeadline]:
    reference = reference or date.today()
    horizon_end = reference + timedelta(days=horizon_days)

    if rule.kind == AccountingReminderRule.ReminderKind.VAT_QUARTERLY_FILING:
        year, quarter = current_quarter(reference)
        candidates = [
            (year, quarter),
            (year, quarter + 1) if quarter < 4 else (year + 1, 1),
        ]
        for y, q in candidates:
            due = vat_quarterly_filing_deadline(y, q)
            if reference <= due <= horizon_end:
                yield ReminderDeadline(
                    period_key=f'{y}-Q{q}',
                    due_date=due,
                    title=f'USt-Voranmeldung Q{q} {y}',
                    body_lines=[
                        f'Quarterly VAT pre-registration (USt-Voranmeldung) for Q{q} {y} '
                        f'is due on {due.isoformat()}.',
                        'Run: python manage.py vat_quarterly_report '
                        f'--entity=<slug> --year={y} --quarter={q}',
                        'Hand the JSON output to your Steuerberater or file via ELSTER.',
                    ],
                )

    elif rule.kind == AccountingReminderRule.ReminderKind.MONTHLY_BOOKKEEPING:
        month_ref = date(reference.year, reference.month, 1)
        for offset in (0, 1):
            y = month_ref.year
            m = month_ref.month + offset
            if m > 12:
                y += 1
                m = 1
            period = date(y, m, 1)
            due = monthly_bookkeeping_deadline(period)
            if reference <= due <= horizon_end:
                yield ReminderDeadline(
                    period_key=f'{period.year}-{period.month:02d}',
                    due_date=due,
                    title=f'Monthly bookkeeping — {period.strftime("%B %Y")}',
                    body_lines=[
                        f'Close books for {period.strftime("%B %Y")} by {due.isoformat()}.',
                        'Run: python manage.py accounting_health_check --entity=<slug>',
                        'Import bank CSV, link Belege, approve draft invoices from webapp imports.',
                    ],
                )

    elif rule.kind == AccountingReminderRule.ReminderKind.KLEINUNTERNEHMER_QUARTERLY:
        year, quarter = current_quarter(reference)
        _, period_end = quarter_date_range(year, quarter)
        due = period_end + timedelta(days=14)
        if reference <= due <= horizon_end:
            yield ReminderDeadline(
                period_key=f'{year}-Q{quarter}',
                due_date=due,
                title=f'Kleinunternehmer turnover check Q{quarter} {year}',
                body_lines=[
                    f'Review turnover against § 19 UStG limits for Q{quarter} {year}.',
                    'Run: python manage.py vat_quarterly_report --entity=<slug> '
                    f'--year={year} --quarter={quarter}',
                ],
            )

    elif rule.kind == AccountingReminderRule.ReminderKind.YEAR_END_HANDOFF:
        due = year_end_handoff_deadline(reference.year - 1)
        if reference <= due <= horizon_end:
            prior = reference.year - 1
            yield ReminderDeadline(
                period_key=f'{prior}-YE',
                due_date=due,
                title=f'Year-end handoff {prior}',
                body_lines=[
                    f'Send {prior} posted books and Belege index to your Steuerberater '
                    f'by {due.isoformat()}.',
                    'Run: python manage.py export_steuerberater '
                    f'--entity=<slug> --year={prior}',
                ],
            )

    elif rule.kind == AccountingReminderRule.ReminderKind.CUSTOM:
        if not rule.custom_month or not rule.custom_day:
            return
        due = _safe_date(reference.year, rule.custom_month, rule.custom_day)
        if due < reference:
            due = _safe_date(reference.year + 1, rule.custom_month, rule.custom_day)
        if reference <= due <= horizon_end:
            title = rule.title or 'Custom accounting deadline'
            yield ReminderDeadline(
                period_key=f'custom-{due.isoformat()}',
                due_date=due,
                title=title,
                body_lines=[
                    f'{title} is due on {due.isoformat()}.',
                    rule.notes or 'See your accounting checklist.',
                ],
            )


def should_send_reminder(
    *,
    due_date: date,
    lead_days: int,
    today: date,
    grace_days: int,
) -> bool:
    send_from = due_date - timedelta(days=lead_days)
    send_until = send_from + timedelta(days=grace_days)
    return send_from <= today <= send_until
