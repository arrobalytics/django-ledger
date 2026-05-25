"""
Runtime registration of additional account roles from regional plugins.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

from django.utils.translation import gettext_lazy as _


def register_extra_roles(
    asset_roles: Iterable[Tuple[str, str]] = (),
    liability_roles: Iterable[Tuple[str, str]] = (),
    equity_roles: Iterable[Tuple[str, str]] = (),
    income_roles: Iterable[Tuple[str, str]] = (),
    cogs_roles: Iterable[Tuple[str, str]] = (),
    expense_roles: Iterable[Tuple[str, str]] = (),
    group_memberships: dict | None = None,
) -> None:
    """
    Extend ``django_ledger.io.roles`` with country-specific roles at startup.

    Parameters
    ----------
    asset_roles, liability_roles, ...
        Iterables of ``(role_id, verbose_label)`` tuples.
    group_memberships:
        Mapping of ``GROUP_*`` constant names to lists of role ids, e.g.
        ``{'GROUP_CURRENT_ASSETS': ['asset_ca_vat_recv']}``.
    """
    from django_ledger.io import roles as roles_module

    category_map = [
        ('ASSET', asset_roles, 0, 0),
        ('LIABILITY', liability_roles, 1, 1),
        ('EQUITY', equity_roles, 2, 2),
        ('INCOME', income_roles, 2, 3),
        ('COGS', cogs_roles, 2, 4),
        ('EXPENSE', expense_roles, 2, 5),
    ]

    for category, role_items, choice_index, form_choice_index in category_map:
        new_roles: List[Tuple[str, str]] = [(r, _(label)) for r, label in role_items]
        if not new_roles:
            continue

        for role_id, label in new_roles:
            const_name = role_id.upper()
            setattr(roles_module, const_name, role_id)
            roles_module.VALID_ROLES.append(role_id)
            roles_module.BS_ROLES[role_id] = category
            roles_module.ACCOUNT_LIST_ROLE_ORDER.append(role_id)
            roles_module.ACCOUNT_LIST_ROLE_VERBOSE[role_id] = label

        roles_module.ACCOUNT_ROLE_CHOICES[choice_index][1].extend(new_roles)
        if form_choice_index < len(roles_module.ACCOUNT_ROLE_CHOICES_FOR_FORMS):
            roles_module.ACCOUNT_ROLE_CHOICES_FOR_FORMS[form_choice_index][1].extend(new_roles)

    if group_memberships:
        for group_name, role_ids in group_memberships.items():
            group = getattr(roles_module, group_name)
            group.extend(role_ids)
            group[:] = list(set(group))
