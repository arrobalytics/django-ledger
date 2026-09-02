"""
Smoke tests for EntityModel URL helper methods.

These tests verify that model URL helpers resolve to entity-scoped URL strings
without exercising view permissions or HTTP responses.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.entity import EntityModel


class EntityURLHelpersAPITest(TestCase):
    URL_HELPERS = (
        "get_absolute_url",
        "get_dashboard_url",
        "get_manage_url",
        "get_ledgers_url",
        "get_bills_url",
        "get_invoices_url",
        "get_banks_url",
        "get_balance_sheet_url",
        "get_income_statement_url",
        "get_cashflow_statement_url",
        "get_data_import_url",
        "get_coa_list_url",
        "get_coa_list_inactive_url",
        "get_coa_create_url",
        "get_accounts_url",
        "get_customers_url",
        "get_vendors_url",
        "get_delete_url",
    )

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_entity_url_helpers_admin",
            email="api-entity-url-helpers-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.entity_model = EntityModel.create_entity(
            name="API Entity URL Helpers Entity",
            admin=cls.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        cls.entity_model.create_chart_of_accounts(
            coa_name="API Entity URL Helpers CoA",
            commit=True,
            assign_as_default=True,
        )

    def test_url_helpers_return_entity_scoped_urls(self):
        for helper_name in self.URL_HELPERS:
            with self.subTest(helper_name=helper_name):
                url = getattr(self.entity_model, helper_name)()

                self.assertIsInstance(url, str)
                self.assertTrue(url)
                self.assertIn(self.entity_model.slug, url)
