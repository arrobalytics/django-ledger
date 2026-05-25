"""
SKR03 chart of accounts loader.

Full SKR03 data can be supplied via ``DJANGO_LEDGER_DE_SKR03_DATA`` or by
extending ``DEFAULT_SKR03_ACCOUNTS`` in this module.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional

from django.conf import settings

from django_ledger.io import roles
from django_ledger.models.coa_default import PREFIX_MAP, build_chart_of_accounts_root_map

from django_ledger_countries.de.roles import (
    ASSET_CA_VAT_RECEIVABLE,
    LIABILITY_CL_VAT_PAYABLE,
)


def _account(
    code: str,
    role: str,
    balance_type: str,
    name: str,
    name_en: str,
) -> Dict:
    return {
        'code': code,
        'role': role,
        'balance_type': balance_type,
        'name': name,
        'name_en': name_en,
        'parent': None,
    }


# Starter subset — replace/extend with your full SKR03 dataset.
DEFAULT_SKR03_ACCOUNTS: List[Dict] = [
    _account('1200', roles.ASSET_CA_CASH, 'debit', 'Bank', 'Bank'),
    _account('1400', roles.ASSET_CA_RECEIVABLES, 'debit', 'Forderungen aus L&L', 'Trade receivables'),
    _account('1576', ASSET_CA_VAT_RECEIVABLE, 'debit', 'Abziehbare Vorsteuer 19%', 'Input VAT 19%'),
    _account('1600', roles.LIABILITY_CL_ACC_PAYABLE, 'credit', 'Verbindlichkeiten aus L&L', 'Trade payables'),
    _account('1776', LIABILITY_CL_VAT_PAYABLE, 'credit', 'Umsatzsteuer 19%', 'Output VAT 19%'),
    _account('1800', roles.LIABILITY_CL_OTHER, 'credit', 'Sonstige Verbindlichkeiten', 'Other payables'),
    _account('8400', roles.INCOME_OPERATIONAL, 'credit', 'Erlöse 19% USt', 'Revenue 19% VAT'),
    _account('8500', roles.INCOME_OPERATIONAL, 'credit', 'Erlöse steuerfrei', 'Tax-exempt revenue'),
    _account('4000', roles.EXPENSE_OPERATIONAL, 'debit', 'Wareneingang 19% Vorsteuer', 'Purchases 19% VAT'),
    _account('4900', roles.EXPENSE_OTHER, 'debit', 'Sonstige betriebliche Aufwendungen', 'Other operating expense'),
]


def get_skr03_accounts() -> List[Dict]:
    custom = getattr(settings, 'DJANGO_LEDGER_DE_SKR03_DATA', None)
    source = custom if custom is not None else DEFAULT_SKR03_ACCOUNTS
    accounts = deepcopy(source)
    for account in accounts:
        account.setdefault('parent', None)
        account['root_group'] = PREFIX_MAP[account['role'].split('_')[0]]
    return accounts


def get_skr03_root_map() -> Dict:
    return build_chart_of_accounts_root_map(get_skr03_accounts())


def get_account_translations(accounts: Optional[List[Dict]] = None) -> List[Dict]:
    accounts = accounts or get_skr03_accounts()
    translations = []
    for account in accounts:
        translations.append({'code': account['code'], 'locale': 'de', 'name': account['name']})
        if name_en := account.get('name_en'):
            translations.append({'code': account['code'], 'locale': 'en', 'name': name_en})
    return translations
