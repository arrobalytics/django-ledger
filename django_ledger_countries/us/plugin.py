"""
United States regional plugin — passthrough to core django-ledger defaults.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from django_ledger.regional.base import RegionalPlugin
from django_ledger.regional.us_fallback import USRegionalPlugin as _USDefaults


class USRegionalPlugin(_USDefaults, RegionalPlugin):
    code = 'us'

    def get_default_coa(self, entity) -> Optional[List[Dict]]:
        return None

    def get_setting_defaults(self) -> Dict[str, Any]:
        return super().get_setting_defaults()
