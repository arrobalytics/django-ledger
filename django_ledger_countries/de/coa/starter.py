"""
Default active SKR03 accounts for a Bildungsurlaub training provider.

Online and in-person accredited courses: student fees, freelance teachers,
venue rental, video/IT gear, website hosting, accreditation and professional
fees (tax advisor, year-end), marketing, and day-to-day admin.

All postable DATEV accounts are loaded onto the chart; only this starter set is
``active=True`` by default so journal entry pickers stay manageable. Activate
more accounts from the chart of accounts UI when needed.
"""
from __future__ import annotations

from typing import FrozenSet, Iterable, Set

from django.conf import settings

# Override via DJANGO_LEDGER_DE_SKR03_STARTER_CODES.
DEFAULT_SCHOOL_STARTER_CODES: tuple[str, ...] = (
    # Balance sheet / clearing
    '0860 00',  # Gewinnvortrag (opening / year-end equity)
    '1200 00',  # Bank
    '1400 00',  # Student / customer receivables (unpaid invoices)
    '1600 00',  # Trade payables (unpaid bills)
    '1576 00',  # Input VAT 19% (Vorsteuer)
    '1776 00',  # Output VAT 19% (Umsatzsteuer)
    # Course revenue
    '8100 00',  # Tax-exempt sales (typical Bildungsurlaub / § 4 UStG)
    '8200 00',  # General revenue (course fees)
    '8000 00',  # Sales revenue (freely assignable)
    '8001 10',  # Enrollment / admission fees
    '8400 00',  # Taxable revenue 19% (if any services are VAT-able)
    # People & subcontractors
    '3100 11',  # Honoraria — freelance teachers
    '3100 28',  # Consulting / advisory services purchased
    '3100 90',  # Other third-party services
    # Premises & equipment
    '4210 10',  # Room rental (in-person course locations)
    '4960 00',  # Rental of movable equipment / furnishings
    '4810 00',  # Equipment leasing (e.g. video gear)
    '0300 10',  # Capitalized school / AV equipment
    '4805 00',  # Repairs & maintenance of equipment
    '4855 00',  # Immediate write-off of low-value assets (GWG)
    # Website & IT
    '4806 00',  # Hosting / software maintenance
    '4920 00',  # Telephone / telecom
    '4980 10',  # IT consumables (cables, small gear)
    # Professional, regulatory & admin
    '4390 10',  # Fees (accreditation, permits, registrations)
    '4950 11',  # Consulting costs (legal / general advisory)
    '4955 00',  # Bookkeeping / tax advisor (Steuerberater)
    '4957 00',  # Year-end closing & audit costs
    '4360 00',  # Insurance
    '4600 15',  # Advertising / course marketing
    '4670 00',  # Owner travel (in-person courses, site visits)
    '4970 00',  # Bank charges / payment fees
    '4997 00',  # General administration
)


def get_starter_account_codes() -> FrozenSet[str]:
    configured = getattr(settings, 'DJANGO_LEDGER_DE_SKR03_STARTER_CODES', None)
    if configured is not None:
        return frozenset(configured)
    return frozenset(DEFAULT_SCHOOL_STARTER_CODES)


def apply_starter_activation(coa_model, starter_codes: Iterable[str] | None = None) -> int:
    """
    Activate only *starter_codes* on *coa_model*; deactivate all other non-root accounts.
    Returns the number of active accounts.
    """
    starter = frozenset(starter_codes) if starter_codes is not None else get_starter_account_codes()
    qs = coa_model.accountmodel_set.not_coa_root()
    qs.exclude(code__in=starter).update(active=False)
    qs.filter(code__in=starter).update(active=True)
    return qs.filter(active=True).count()


def mark_account_activation(accounts: list[dict], starter_codes: Set[str] | None = None) -> list[dict]:
    starter = starter_codes if starter_codes is not None else set(get_starter_account_codes())
    for account in accounts:
        account['active'] = account['code'] in starter
    return accounts
