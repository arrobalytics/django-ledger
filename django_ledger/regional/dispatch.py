"""
Thin dispatch helpers called from core django-ledger code paths.
"""
from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

from django_ledger.regional.registry import get_country_plugin

if TYPE_CHECKING:
    from django_ledger.models.entity import EntityModel
    from django_ledger.models.journal_entry import JournalEntryModel
    from django_ledger.models.transactions import TransactionModel


def get_regional_default_coa(entity: EntityModel) -> Optional[List[Dict]]:
    return get_country_plugin().get_default_coa(entity)


def dispatch_adjust_posting(document, transactions: List[TransactionModel]) -> List[TransactionModel]:
    return get_country_plugin().adjust_posting(document, transactions)


def dispatch_on_journal_entry_posted(journal_entry: JournalEntryModel, *, committed: bool = True) -> None:
    get_country_plugin().on_journal_entry_posted(journal_entry, committed=committed)


def dispatch_validate_journal_entry(journal_entry: JournalEntryModel) -> None:
    get_country_plugin().validate_journal_entry(journal_entry)


def dispatch_on_entity_created(entity: EntityModel) -> None:
    get_country_plugin().on_entity_created(entity)


def dispatch_on_coa_populated(entity: EntityModel, coa_model) -> None:
    get_country_plugin().on_coa_populated(entity, coa_model)


def dispatch_validate_account_code(code: str) -> None:
    get_country_plugin().validate_account_code(code)


def should_enforce_account_code_prefix() -> bool:
    return get_country_plugin().enforce_account_code_prefix()
