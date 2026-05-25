"""
Abstract base class for country / regional plugins.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from django_ledger.models.entity import EntityModel
    from django_ledger.models.journal_entry import JournalEntryModel
    from django_ledger.models.transactions import TransactionModel


class RegionalPlugin(ABC):
    """
    Contract implemented by each country package under ``django_ledger_countries``.
    """

    code: str = ''

    @abstractmethod
    def get_setting_defaults(self) -> Dict[str, Any]:
        """Return default values for country-scoped ledger settings."""

    def get_default_coa(self, entity: EntityModel) -> Optional[List[Dict]]:
        """
        Return a chart-of-accounts list for *entity*, or ``None`` to use the
        core US default from ``coa_default.get_default_coa()``.
        """
        return None

    def register_roles(self) -> None:
        """Register country-specific account roles into ``django_ledger.io.roles``."""

    def on_entity_created(self, entity: EntityModel) -> None:
        """Hook after a new entity is persisted."""

    def on_coa_populated(self, entity: EntityModel, coa_model) -> None:
        """Hook after default accounts are inserted into a chart of accounts."""

    def adjust_posting(
        self,
        document,
        transactions: List[TransactionModel],
    ) -> List[TransactionModel]:
        """
        Adjust or extend *transactions* before they are persisted during
        ``AccrualMixIn.migrate_state()``.
        """
        return transactions

    def on_journal_entry_posted(
        self,
        journal_entry: JournalEntryModel,
        *,
        committed: bool = True,
    ) -> None:
        """Hook after a journal entry is marked posted."""

    def validate_journal_entry(self, journal_entry: JournalEntryModel) -> None:
        """Raise ``ValidationError`` when posting rules are violated."""

    def validate_account_code(self, code: str) -> None:
        """Raise ``ValidationError`` when *code* is invalid for this country."""

    def enforce_account_code_prefix(self) -> bool:
        """When False, skip US-style role prefix checks on account codes."""
        return True
