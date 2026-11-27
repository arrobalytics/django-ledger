"""
High-level API tests for PurchaseOrderModel queryset and manager behavior.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import PurchaseOrderModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.purchase_order import PurchaseOrderModelValidationError


class PurchaseOrderQuerySetAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="api_purchase_order_queryset_admin",
            email="api-purchase-order-queryset-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_purchase_order_queryset_manager",
            email="api-purchase-order-queryset-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_purchase_order_queryset_other_admin",
            email="api-purchase-order-queryset-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_purchase_order_queryset_unrelated",
            email="api-purchase-order-queryset-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_purchase_order_queryset_superuser",
            email="api-purchase-order-queryset-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Purchase Order Queryset Entity", admin_user=None, manager_user=None):
        entity_model = EntityModel.create_entity(
            name=name,
            admin=admin_user or self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        if manager_user is not None:
            entity_model.managers.add(manager_user)
        return entity_model

    def create_purchase_order(
        self,
        entity_model,
        *,
        title="API Purchase Order Queryset PO",
        status=PurchaseOrderModel.PO_STATUS_DRAFT,
    ):
        po_model = PurchaseOrderModel()
        po_model.configure(
            entity_slug=entity_model,
            po_title=title,
            user_model=self.admin_user,
            draft_date=date(2026, 1, 15),
            commit=True,
        )
        if status != PurchaseOrderModel.PO_STATUS_DRAFT:
            po_model.po_status = status
            po_model.save(update_fields=["po_status", "updated"])
            po_model.refresh_from_db()
        return po_model

    def assert_po_uuids(self, queryset, expected_purchase_orders):
        self.assertEqual(
            set(queryset.values_list("uuid", flat=True)),
            {po_model.uuid for po_model in expected_purchase_orders},
        )

    def test_for_entity_accepts_model_slug_and_uuid(self):
        entity_model = self.create_entity(name="API Purchase Order Queryset Entity A")
        other_entity_model = self.create_entity(
            name="API Purchase Order Queryset Entity B",
            admin_user=self.other_admin_user,
        )
        po_model = self.create_purchase_order(entity_model)
        self.create_purchase_order(other_entity_model, title="API Other Purchase Order Queryset PO")

        self.assert_po_uuids(PurchaseOrderModel.objects.for_entity(entity_model), [po_model])
        self.assert_po_uuids(PurchaseOrderModel.objects.for_entity(entity_model.slug), [po_model])
        self.assert_po_uuids(PurchaseOrderModel.objects.for_entity(entity_model.uuid), [po_model])

    def test_for_entity_rejects_invalid_input_and_missing_slug_returns_empty_queryset(self):
        self.create_purchase_order(self.create_entity())

        with self.assertRaises(PurchaseOrderModelValidationError):
            PurchaseOrderModel.objects.for_entity(object())

        self.assertFalse(PurchaseOrderModel.objects.for_entity("missing-purchase-order-entity-slug").exists())

    def test_for_user_scopes_to_authorized_users_and_superuser(self):
        entity_model = self.create_entity(
            name="API Purchase Order Queryset Access Entity",
            manager_user=self.manager_user,
        )
        other_entity_model = self.create_entity(
            name="API Purchase Order Queryset Other Access Entity",
            admin_user=self.other_admin_user,
        )
        po_model = self.create_purchase_order(entity_model)
        other_po_model = self.create_purchase_order(other_entity_model, title="API Other Access Purchase Order")

        self.assert_po_uuids(PurchaseOrderModel.objects.all().for_user(self.admin_user), [po_model])
        self.assert_po_uuids(PurchaseOrderModel.objects.all().for_user(self.manager_user), [po_model])
        self.assertFalse(PurchaseOrderModel.objects.all().for_user(self.unrelated_user).exists())
        self.assert_po_uuids(
            PurchaseOrderModel.objects.all().for_user(self.superuser),
            [po_model, other_po_model],
        )

    def test_status_filters_return_purchase_orders_by_public_status(self):
        entity_model = self.create_entity(name="API Purchase Order Queryset Status Entity")
        draft_po = self.create_purchase_order(entity_model, title="API Draft Purchase Order")
        approved_po = self.create_purchase_order(
            entity_model,
            title="API Approved Purchase Order",
            status=PurchaseOrderModel.PO_STATUS_APPROVED,
        )
        fulfilled_po = self.create_purchase_order(
            entity_model,
            title="API Fulfilled Purchase Order",
            status=PurchaseOrderModel.PO_STATUS_FULFILLED,
        )

        purchase_order_qs = PurchaseOrderModel.objects.for_entity(entity_model)

        self.assert_po_uuids(purchase_order_qs.draft(), [draft_po])
        self.assert_po_uuids(purchase_order_qs.approved(), [approved_po])
        self.assert_po_uuids(purchase_order_qs.fulfilled(), [fulfilled_po])
        self.assert_po_uuids(purchase_order_qs.active(), [approved_po, fulfilled_po])
