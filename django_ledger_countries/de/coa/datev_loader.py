"""
Load DATEV SKR03 chart exports (CSV) into django-ledger account dicts.

Expects DATEV Branchenpaket CSV columns such as those in
``2026_Schulen_freie_Träger.csv`` (account codes kept in native ``NNNN NN`` form).
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.conf import settings

from django_ledger.io import roles
from django_ledger.io.roles import CREDIT, DEBIT

from django_ledger_countries.de.roles import (
    ASSET_CA_VAT_RECEIVABLE,
    LIABILITY_CL_VAT_PAYABLE,
)
from django_ledger_countries.de.coa.starter import get_starter_account_codes, mark_account_activation
from django_ledger_countries.de.validators import parse_datev_account_code, validate_datev_account_code

DEFAULT_CSV_FILENAME = '2026_Schulen_freie_Träger.csv'


def default_csv_path() -> Path:
    return Path(__file__).resolve().parent / 'skr03' / DEFAULT_CSV_FILENAME


def resolve_csv_path() -> Path:
    configured = getattr(settings, 'DJANGO_LEDGER_DE_SKR03_CSV', None)
    if configured:
        return Path(configured)
    return default_csv_path()


def load_datev_coa_rows(csv_path: Optional[Path] = None) -> List[Dict]:
    path = csv_path or resolve_csv_path()
    if not path.exists():
        raise FileNotFoundError(f'SKR03 CSV not found: {path}')

    rows: List[Dict] = []
    with path.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if row.get('is_postable') != 'true':
                continue
            if row.get('is_range') == 'true':
                continue
            code = row['account_number'].strip()
            validate_datev_account_code(code)
            role, balance_type = map_skr03_account(
                account_class=row['account_class'],
                account_number=code,
                account_name_de=row['account_name_de'],
            )
            rows.append(
                {
                    'code': code,
                    'role': role,
                    'balance_type': balance_type,
                    'name': row['account_name_de'].strip(),
                    'name_en': (row.get('account_name_en') or '').strip(),
                    'parent': None,
                    'account_class': row['account_class'],
                    'account_group_de': row.get('account_group_de', ''),
                    'datev_edition': getattr(settings, 'DJANGO_LEDGER_DE_SKR03_EDITION', DEFAULT_CSV_FILENAME),
                }
            )
    return mark_account_activation(rows, set(get_starter_account_codes()))


def map_skr03_account(
    account_class: str,
    account_number: str,
    account_name_de: str,
) -> Tuple[str, str]:
    main, _suffix = parse_datev_account_code(account_number)
    name = account_name_de.lower()

    if account_class == '8' or account_class == '5':
        return roles.INCOME_OPERATIONAL, CREDIT
    if account_class in {'4', '6', '7'}:
        return roles.EXPENSE_OPERATIONAL, DEBIT
    if account_class == '3':
        return roles.ASSET_CA_INVENTORY, DEBIT
    if account_class == '2':
        if 'verbindlich' in name or 'passiv' in name or 'ertrag' in name:
            return roles.LIABILITY_CL_DEFERRED_REVENUE, CREDIT
        return roles.ASSET_CA_PREPAID, DEBIT
    if account_class == '9':
        return roles.EXPENSE_OTHER, DEBIT
    if account_class == '1':
        return _map_class_1(main, name)
    if account_class == '0':
        return _map_class_0(main, name)

    return roles.EXPENSE_OTHER, DEBIT


def _map_class_1(main: int, name: str) -> Tuple[str, str]:
    if 'vorsteuer' in name or 1570 <= main <= 1579:
        return ASSET_CA_VAT_RECEIVABLE, DEBIT
    if 'umsatzsteuer' in name or (1770 <= main <= 1789):
        return LIABILITY_CL_VAT_PAYABLE, CREDIT
    if 'verbindlich' in name:
        if 'steuer' in name or 'lohn' in name or 'sozial' in name or 1730 <= main <= 1799:
            return roles.LIABILITY_CL_TAXES_PAYABLE, CREDIT
        if 1600 <= main <= 1729:
            return roles.LIABILITY_CL_ACC_PAYABLE, CREDIT
        return roles.LIABILITY_CL_OTHER, CREDIT
    if 'forderung' in name or 'debitor' in name or 1400 <= main <= 1499:
        return roles.ASSET_CA_RECEIVABLES, DEBIT
    if 'bank' in name or 1200 <= main <= 1299:
        return roles.ASSET_CA_CASH, DEBIT
    if 'kasse' in name or 1000 <= main <= 1099:
        return roles.ASSET_CA_CASH, DEBIT
    if 'wertpapier' in name or 'scheck' in name or 1300 <= main <= 1399:
        return roles.ASSET_CA_MKT_SECURITIES, DEBIT
    return roles.ASSET_CA_OTHER, DEBIT


def _map_class_0(main: int, name: str) -> Tuple[str, str]:
    if 'verbindlich' in name or 630 <= main <= 799:
        if main >= 700 or 'lang' in name:
            return roles.LIABILITY_LTL_NOTES_PAYABLE, CREDIT
        return roles.LIABILITY_CL_OTHER, CREDIT
    if (
        'kapital' in name
        or 'rücklage' in name
        or 'gewinn' in name
        or 'verlust' in name
        or 'eigenkapital' in name
        or 800 <= main <= 999
    ):
        return roles.EQUITY_CAPITAL, CREDIT
    if 'abschreib' in name or 'kumulierte' in name:
        return roles.ASSET_PPE_BUILDINGS_ACCUM_DEPRECIATION, CREDIT
    if 'grundst' in name or 'gebäud' in name or 'bauten' in name or 'bau ' in name:
        return roles.ASSET_PPE_BUILDINGS, DEBIT
    if 'maschine' in name or 'fahrzeug' in name or 'anlage' in name:
        return roles.ASSET_PPE_EQUIPMENT, DEBIT
    if (
        'immateriell' in name
        or 'koncession' in name
        or 'software' in name
        or 'lizenz' in name
        or 'goodwill' in name
        or main < 100
    ):
        return roles.ASSET_INTANGIBLE_ASSETS, DEBIT
    if 'beteilig' in name or 'ausleihung' in name or 'wertpapier' in name:
        return roles.ASSET_LTI_SECURITIES, DEBIT
    return roles.ASSET_PPE_EQUIPMENT, DEBIT


@lru_cache(maxsize=1)
def get_cached_datev_accounts() -> Tuple[Dict, ...]:
    return tuple(load_datev_coa_rows())


def clear_datev_coa_cache() -> None:
    get_cached_datev_accounts.cache_clear()


def get_account_translations_from_rows(rows: Optional[List[Dict]] = None) -> List[Dict]:
    rows = rows or list(get_cached_datev_accounts())
    translations: List[Dict] = []
    for account in rows:
        translations.append({'code': account['code'], 'locale': 'de', 'name': account['name']})
        if name_en := account.get('name_en'):
            translations.append({'code': account['code'], 'locale': 'en', 'name': name_en})
    return translations
