"""
High-level API tests for BillModel queryset and manager behavior.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.vendor import VendorModel


class BillQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_bill_queryset_admin",
            email="api-bill-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_bill_queryset_manager",
            email="api-bill-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_bill_queryset_other_admin",
            email="api-bill-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_bill_queryset_unrelated",
            email="api-bill-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_bill_queryset_superuser",
            email="api-bill-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity_setup(self, *, name="API Bill Queryset Entity", admin_user=None, manager_user=None):
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
        cash_account = coa_model.create_account(
            code="1010",
            name=f"{name} Cash Account",
            role="asset_ca_cash",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        prepaid_account = coa_model.create_account(
            code="1310",
            name=f"{name} Prepaid Account",
            role="asset_ca_prepaid",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        payable_account = coa_model.create_account(
            code="2010",
            name=f"{name} Accounts Payable",
            role="lia_cl_acc_payable",
            balance_type="credit",
            active=True,
            is_role_default=True,
        )
        expense_account = coa_model.create_account(
            code="6010",
            name=f"{name} Expense Account",
            role="ex_regular",
            balance_type="debit",
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f"{name} Unit",
            unit_abbr=f"{name[:8].lower().replace(' ', '-')}-u",
            active=True,
            commit=True,
        )
        vendor_model = VendorModel(
            vendor_name=f"{name} Vendor",
            entity_model=entity_model,
            description=f"{name} Vendor description",
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()
        expense_item = entity_model.create_item_expense(
            name=f"{name} Expense Item",
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        return {
            "entity_model": entity_model,
            "cash_account": cash_account,
            "prepaid_account": prepaid_account,
            "payable_account": payable_account,
            "vendor_model": vendor_model,
            "expense_item": expense_item,
        }

    def create_bill(self, setup, *, date_draft=date(2026, 1, 15)):
        bill_model = BillModel(
            vendor=setup["vendor_model"],
            terms=BillModel.TERMS_NET_30,
            cash_account=setup["cash_account"],
            prepaid_account=setup["prepaid_account"],
            unearned_account=setup["payable_account"],
        )
        _ledger_model, bill_model = bill_model.configure(
            entity_slug=setup["entity_model"],
            user_model=self.admin_user,
            date_draft=date_draft,
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def migrate_expense_item(self, bill_model, setup, *, quantity="2.00", unit_cost="50.00"):
        quantity = Decimal(quantity)
        unit_cost = Decimal(unit_cost)
        bill_model.migrate_itemtxs(
            itemtxs={
                setup["expense_item"].item_number: {
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "total_amount": quantity * unit_cost,
                }
            },
            operation=BillModel.ITEMIZE_REPLACE,
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def move_to_review(self, bill_model, setup):
        bill_model = self.migrate_expense_item(bill_model, setup)
        bill_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        bill_model.refresh_from_db()
        return bill_model

    def move_to_approved(self, bill_model, setup):
        bill_model = self.move_to_review(bill_model, setup)
        bill_model.mark_as_approved(
            entity_slug=setup["entity_model"],
            user_model=self.admin_user,
            date_approved=date(2026, 1, 17),
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def move_to_paid(self, bill_model, setup):
        bill_model = self.move_to_approved(bill_model, setup)
        bill_model.mark_as_paid(
            entity_slug=setup["entity_model"],
            user_model=self.admin_user,
            date_paid=date(2026, 1, 18),
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def move_to_void(self, bill_model, setup):
        bill_model = self.move_to_approved(bill_model, setup)
        bill_model.mark_as_void(
            entity_slug=setup["entity_model"],
            user_model=self.admin_user,
            date_void=date(2026, 1, 19),
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def move_to_canceled(self, bill_model):
        bill_model.mark_as_canceled(date_canceled=date(2026, 1, 20), commit=True)
        bill_model.refresh_from_db()
        return bill_model

    def assert_bill_uuids(self, queryset, expected_bills):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {bill_model.uuid for bill_model in expected_bills},
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        setup = self.create_entity_setup(name="API Bill Queryset Entity A")
        other_setup = self.create_entity_setup(
            name="API Bill Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        bill_model = self.create_bill(setup)
        self.create_bill(other_setup)
        entity_model = setup["entity_model"]

        self.assert_bill_uuids(BillModel.objects.for_entity(entity_model), [bill_model])
        self.assert_bill_uuids(BillModel.objects.for_entity(entity_model.slug), [bill_model])
        self.assert_bill_uuids(BillModel.objects.for_entity(entity_model.uuid), [bill_model])

    def test_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_bill(self.create_entity_setup())

        from django_ledger.models.bill import BillModelValidationError

        with self.assertRaises(BillModelValidationError):
            BillModel.objects.for_entity(object())

        self.assertFalse(BillModel.objects.for_entity("missing-bill-entity-slug").exists())

    def test_for_user_scopes_to_authorized_users_and_superuser(self):
        setup = self.create_entity_setup(
            name="API Bill Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_setup = self.create_entity_setup(
            name="API Bill Queryset Other Access Entity",
            admin_user=self.other_admin_user,
        )
        bill_model = self.create_bill(setup)
        other_bill_model = self.create_bill(other_setup)

        self.assert_bill_uuids(BillModel.objects.all().for_user(self.admin_user), [bill_model])
        self.assert_bill_uuids(BillModel.objects.all().for_user(self.manager_user), [bill_model])
        self.assertFalse(BillModel.objects.all().for_user(self.unrelated_user).exists())
        self.assert_bill_uuids(BillModel.objects.all().for_user(self.superuser), [bill_model, other_bill_model])

    def test_status_filters_return_matching_bills(self):
        setup = self.create_entity_setup(name="API Bill Queryset Status Entity")
        draft_bill = self.create_bill(setup)
        review_bill = self.move_to_review(self.create_bill(setup), setup)
        approved_bill = self.move_to_approved(self.create_bill(setup), setup)
        paid_bill = self.move_to_paid(self.create_bill(setup), setup)
        void_bill = self.move_to_void(self.create_bill(setup), setup)
        canceled_bill = self.move_to_canceled(self.create_bill(setup))

        bills_qs = BillModel.objects.for_entity(setup["entity_model"])

        self.assert_bill_uuids(bills_qs.draft(), [draft_bill])
        self.assert_bill_uuids(bills_qs.in_review(), [review_bill])
        self.assert_bill_uuids(bills_qs.approved(), [approved_bill])
        self.assert_bill_uuids(bills_qs.paid(), [paid_bill])
        self.assert_bill_uuids(bills_qs.void(), [void_bill])
        self.assert_bill_uuids(bills_qs.canceled(), [canceled_bill])

    def test_semantic_filters_return_active_unpaid_and_overdue_bills(self):
        setup = self.create_entity_setup(name="API Bill Queryset Semantic Entity")
        draft_bill = self.create_bill(setup)
        approved_bill = self.move_to_approved(self.create_bill(setup), setup)
        paid_bill = self.move_to_paid(self.create_bill(setup), setup)
        void_bill = self.move_to_void(self.create_bill(setup), setup)

        overdue_bill = self.create_bill(setup)
        overdue_bill.date_due = date(2000, 1, 1)
        overdue_bill.save(update_fields=["date_due", "updated"])

        future_due_bill = self.create_bill(setup)
        future_due_bill.date_due = date(2099, 1, 1)
        future_due_bill.save(update_fields=["date_due", "updated"])

        bills_qs = BillModel.objects.for_entity(setup["entity_model"])

        self.assert_bill_uuids(bills_qs.active(), [approved_bill, paid_bill])
        self.assert_bill_uuids(bills_qs.unpaid(), [approved_bill])
        self.assertTrue(bills_qs.overdue().filter(uuid=overdue_bill.uuid).exists())
        self.assertFalse(bills_qs.overdue().filter(uuid=future_due_bill.uuid).exists())
        self.assertFalse(bills_qs.active().filter(uuid=draft_bill.uuid).exists())
        self.assertFalse(bills_qs.active().filter(uuid=void_bill.uuid).exists())
