"""
High-level API tests for EstimateModel queryset and manager behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_INVENTORY,
    COGS,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
)
from django_ledger.models import EstimateModel
from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.estimate import EstimateModelValidationError
from django_ledger.models.items import ItemModel


class EstimateQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_estimate_queryset_admin",
            email="api-estimate-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_estimate_queryset_manager",
            email="api-estimate-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_estimate_queryset_other_admin",
            email="api-estimate-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_estimate_queryset_unrelated",
            email="api-estimate-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_estimate_queryset_superuser",
            email="api-estimate-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Estimate Queryset Entity", admin_user=None, manager_user=None):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=admin_user or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        if manager_user is not None:
            entity_model.managers.add(manager_user)

        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f"{name} CoA",
            commit=True,
            assign_as_default=True,
        )
        coa_model.create_account(
            code="1410",
            name=f"{name} Inventory Account",
            role=ASSET_CA_INVENTORY,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="5010",
            name=f"{name} COGS Account",
            role=COGS,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code="4010",
            name=f"{name} Income Account",
            role=INCOME_OPERATIONAL,
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role=EXPENSE_OPERATIONAL,
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f"{name} Unit",
            unit_abbr=f"e-{str(entity_model.uuid)[:6]}",
            active=True,
            commit=True,
        )
        customer_model = CustomerModel(
            customer_name=f"{name} Customer",
            entity_model=entity_model,
            description=f"{name} Customer description",
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        service_item = entity_model.create_item_service(
            name=f"{name} Service Item",
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )
        entity_model.create_item_expense(
            name=f"{name} Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "customer_model": customer_model,
            "service_item": service_item,
        }

    def create_estimate(self, setup, *, date_draft=date(2026, 1, 15), title="API Estimate Queryset Estimate"):
        estimate_model = EstimateModel(terms=EstimateModel.CONTRACT_TERMS_FIXED)
        estimate_model.configure(
            entity_slug=setup["entity_model"],
            customer_model=setup["customer_model"],
            user_model=self.admin_user,
            date_draft=date_draft,
            estimate_title=title,
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def migrate_service_item(self, estimate_model, setup, *, quantity="2.00", unit_cost="50.00", unit_revenue="75.00"):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        unit_revenue = Decimal(unit_revenue)
        estimate_model.migrate_itemtxs(
            itemtxs={
                setup["service_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "unit_revenue": unit_revenue,
                    "total_amount": quantity * unit_revenue,
                }
            },
            operation=EstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def move_to_approved(self, estimate_model, setup):
        estimate_model = self.migrate_service_item(estimate_model, setup)
        estimate_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        estimate_model.refresh_from_db()
        estimate_model.mark_as_approved(commit=True, date_approved=date(2026, 1, 17))
        estimate_model.refresh_from_db()
        return estimate_model

    def move_to_completed(self, estimate_model, setup):
        estimate_model = self.move_to_approved(estimate_model, setup)
        estimate_model.mark_as_completed(commit=True, date_completed=date(2026, 1, 18))
        estimate_model.refresh_from_db()
        return estimate_model

    def assert_estimate_uuids(self, queryset, expected_estimates):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {estimate_model.uuid for estimate_model in expected_estimates},
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API Estimate Queryset Entity A")
        other_setup = self.create_entity_setup(
            name="API Estimate Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        estimate_model = self.create_estimate(setup)
        self.create_estimate(other_setup)
        entity_model = setup["entity_model"]

        self.assert_estimate_uuids(EstimateModel.objects.for_entity(entity_model), [estimate_model])
        self.assert_estimate_uuids(EstimateModel.objects.for_entity(entity_model.slug), [estimate_model])
        self.assert_estimate_uuids(EstimateModel.objects.for_entity(entity_model.uuid), [estimate_model])

    def test_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_estimate(self.create_entity_setup())

        with self.assertRaises(EstimateModelValidationError):
            EstimateModel.objects.for_entity(object())

        self.assertFalse(EstimateModel.objects.for_entity("missing-estimate-entity-slug").exists())

    def test_for_user_scopes_to_authorized_users_and_superuser(self):
        setup = self.create_entity_setup(
            name="API Estimate Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_setup = self.create_entity_setup(
            name="API Estimate Queryset Other Access Entity",
            admin_user=self.other_admin_user,
        )
        estimate_model = self.create_estimate(setup)
        other_estimate_model = self.create_estimate(other_setup)

        self.assert_estimate_uuids(EstimateModel.objects.all().for_user(self.admin_user), [estimate_model])
        self.assert_estimate_uuids(EstimateModel.objects.all().for_user(self.manager_user), [estimate_model])
        self.assertFalse(EstimateModel.objects.all().for_user(self.unrelated_user).exists())
        self.assert_estimate_uuids(
            EstimateModel.objects.all().for_user(self.superuser),
            [estimate_model, other_estimate_model],
        )

    def test_status_filters_return_estimates_and_contracts(self):
        setup = self.create_entity_setup(name="API Estimate Queryset Status Entity")
        draft_estimate = self.create_estimate(setup, title="API Draft Estimate")
        approved_estimate = self.move_to_approved(self.create_estimate(setup, title="API Approved Estimate"), setup)
        completed_estimate = self.move_to_completed(self.create_estimate(setup, title="API Completed Estimate"), setup)

        estimates_qs = EstimateModel.objects.for_entity(setup["entity_model"])

        self.assert_estimate_uuids(estimates_qs.draft(), [draft_estimate])
        self.assert_estimate_uuids(estimates_qs.approved(), [approved_estimate, completed_estimate])
        self.assert_estimate_uuids(estimates_qs.contracts(), [approved_estimate, completed_estimate])
        self.assert_estimate_uuids(estimates_qs.not_approved(), [draft_estimate])
        self.assert_estimate_uuids(estimates_qs.estimates(), [draft_estimate])
