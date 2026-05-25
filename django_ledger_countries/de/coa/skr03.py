"""
SKR03 chart of accounts for Germany.

Loads the DATEV Branchenpaket CSV (default: Schulen freie Träger, 2026) and exposes
account dicts compatible with ``EntityModel.populate_default_coa()``.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional

from django.conf import settings

from django_ledger.models.coa_default import PREFIX_MAP, build_chart_of_accounts_root_map

from django_ledger_countries.de.coa.datev_loader import (
    clear_datev_coa_cache,
    get_account_translations_from_rows,
    get_cached_datev_accounts,
    load_datev_coa_rows,
    resolve_csv_path,
)


def get_skr03_accounts() -> List[Dict]:
    custom = getattr(settings, 'DJANGO_LEDGER_DE_SKR03_DATA', None)
    if custom is not None:
        accounts = deepcopy(custom)
    else:
        accounts = [dict(row) for row in get_cached_datev_accounts()]

    for account in accounts:
        account.setdefault('parent', None)
        account['root_group'] = PREFIX_MAP[account['role'].split('_')[0]]
    return accounts


def get_skr03_root_map() -> Dict:
    return build_chart_of_accounts_root_map(get_skr03_accounts())


def get_account_translations(accounts: Optional[List[Dict]] = None) -> List[Dict]:
    if accounts is None and getattr(settings, 'DJANGO_LEDGER_DE_SKR03_DATA', None) is None:
        return get_account_translations_from_rows()
    return get_account_translations_from_rows(accounts or get_skr03_accounts())


__all__ = [
    'clear_datev_coa_cache',
    'get_account_translations',
    'get_skr03_accounts',
    'get_skr03_root_map',
    'load_datev_coa_rows',
    'resolve_csv_path',
]
