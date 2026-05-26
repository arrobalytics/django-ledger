"""
Germany regional plugin.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from django_ledger.regional.base import RegionalPlugin
from django_ledger_countries.de.coa import skr03
from django_ledger_countries.de.roles import register_german_roles
from django_ledger_countries.de.settings import DE_SETTING_DEFAULTS
from django_ledger_countries.de import vat as vat_module
from django_ledger_countries.de.validators import validate_datev_account_code
from django_ledger_countries.settings import get_ledger_setting


class GermanyRegionalPlugin(RegionalPlugin):
    code = 'de'

    def get_setting_defaults(self) -> Dict[str, Any]:
        return dict(DE_SETTING_DEFAULTS)

    def register_roles(self) -> None:
        register_german_roles()

    def get_default_coa(self, entity) -> Optional[List[Dict]]:
        coa_key = get_ledger_setting('DEFAULT_COA')
        if coa_key == 'skr03':
            return skr03.get_skr03_accounts()
        return None

    def on_entity_created(self, entity) -> None:
        from django_ledger_extensions.models import EntityTaxProfile

        EntityTaxProfile.objects.get_or_create(
            entity=entity,
            defaults=vat_module.get_default_tax_profile_values(),
        )

    def on_coa_populated(self, entity, coa_model) -> None:
        vat_module.apply_regime_starter_activation(coa_model)
        self._seed_account_translations(entity)

    def validate_account_code(self, code: str) -> None:
        validate_datev_account_code(code)

    def enforce_account_code_prefix(self) -> bool:
        return False

    def _seed_account_translations(self, entity) -> None:
        from django_ledger.models.accounts import AccountModel
        from django_ledger_extensions.models import AccountTranslationModel

        coa = entity.default_coa
        if coa is None:
            return

        for entry in skr03.get_account_translations():
            account = coa.accountmodel_set.filter(code=entry['code']).first()
            if account is None:
                continue
            AccountTranslationModel.objects.update_or_create(
                account=account,
                locale=entry['locale'],
                defaults={'name': entry['name']},
            )

    def adjust_posting(self, document, transactions: list) -> list:
        return vat_module.adjust_posting(document, transactions)

    def validate_journal_entry(self, journal_entry) -> None:
        vat_module.validate_vat_journal_entry(journal_entry)

        if not get_ledger_setting('REQUIRE_SUPPORTING_DOCUMENT_ON_POST'):
            return

        from django_ledger_extensions.documents import has_supporting_document_for_posting

        if not has_supporting_document_for_posting(journal_entry):
            raise ValidationError(
                _('A supporting document is required before posting this journal entry.')
            )

    def on_journal_entry_posted(self, journal_entry, *, committed: bool = True) -> None:
        return
