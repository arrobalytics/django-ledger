"""
High-level API behavior tests for bundled default Chart of Accounts data.

These tests validate the shape and grouping of the packaged default CoA
without mutating module-level data.
"""

import importlib.util

from django.test import SimpleTestCase

from django_ledger.io import (
    ROOT_ASSETS,
    ROOT_CAPITAL,
    ROOT_COGS,
    ROOT_EXPENSES,
    ROOT_INCOME,
    ROOT_LIABILITIES,
)
from django_ledger.models.coa_default import (
    CHART_OF_ACCOUNTS_ROOT_MAP,
    get_default_coa,
    get_default_coa_rst,
    verify_unique_code,
)


class CoADefaultAPITest(SimpleTestCase):
    REQUIRED_KEYS = {
        "code",
        "role",
        "balance_type",
        "name",
        "parent",
        "root_group",
    }
    EXPECTED_ROOT_GROUPS = {
        ROOT_ASSETS,
        ROOT_LIABILITIES,
        ROOT_CAPITAL,
        ROOT_INCOME,
        ROOT_COGS,
        ROOT_EXPENSES,
    }

    def test_get_default_coa_returns_entries_with_required_keys(self):
        default_coa = get_default_coa()

        self.assertIsInstance(default_coa, list)
        self.assertGreater(len(default_coa), 0)

        for entry in default_coa:
            with self.subTest(code=entry.get("code")):
                self.assertTrue(self.REQUIRED_KEYS.issubset(entry.keys()))

    def test_default_account_codes_are_unique_and_verified(self):
        default_coa = get_default_coa()
        code_list = [entry["code"] for entry in default_coa]

        self.assertEqual(len(code_list), len(set(code_list)))
        verify_unique_code()

    def test_each_default_account_has_root_group(self):
        for entry in get_default_coa():
            with self.subTest(code=entry["code"]):
                self.assertIn(entry["root_group"], self.EXPECTED_ROOT_GROUPS)

    def test_root_map_groups_accounts_by_root_group(self):
        self.assertTrue(self.EXPECTED_ROOT_GROUPS.issubset(CHART_OF_ACCOUNTS_ROOT_MAP.keys()))

        grouped_codes = set()
        for root_group, entries in CHART_OF_ACCOUNTS_ROOT_MAP.items():
            with self.subTest(root_group=root_group):
                self.assertGreater(len(entries), 0)
                for entry in entries:
                    self.assertEqual(entry["root_group"], root_group)
                    grouped_codes.add(entry["code"])

        self.assertEqual(grouped_codes, {entry["code"] for entry in get_default_coa()})

    def test_get_default_coa_rst_returns_rst_table_when_tabulate_is_available(self):
        if importlib.util.find_spec("tabulate") is None:
            self.skipTest("tabulate is not installed.")

        rst_table = get_default_coa_rst()

        self.assertIsInstance(rst_table, str)
        self.assertIn("code", rst_table)
        self.assertIn("role", rst_table)
