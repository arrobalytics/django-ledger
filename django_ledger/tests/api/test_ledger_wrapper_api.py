"""
High-level API behavior tests for LedgerModel wrapper metadata helpers.

These tests cover wrapper metadata storage and delete eligibility without
exercising bill or invoice lifecycle behavior.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import BillModel, InvoiceModel, LedgerModel
from django_ledger.models.entity import EntityModel


class LedgerWrapperAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_ledger_wrapper_admin",
            email="api-ledger-wrapper-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Ledger Wrapper Entity"):
        return EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_ledger(
        self,
        entity_model,
        *,
        name="API Ledger Wrapper Ledger",
        ledger_xid="api-ledger-wrapper-ledger",
        additional_info=None,
    ):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=ledger_xid,
            entity=entity_model,
            additional_info={} if additional_info is None else additional_info,
        )

    def test_configure_for_wrapper_model_stores_wrapped_model_metadata(self):
        entity_model = self.create_entity(name="API Ledger Wrapper Configure Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-wrapper-configure",
        )
        bill_model = BillModel()

        ledger_model.configure_for_wrapper_model(bill_model)

        wrapped_info = ledger_model.additional_info["wrapped_model"]
        self.assertEqual(wrapped_info["model"], "billmodel")
        self.assertEqual(wrapped_info["uuid"], bill_model.uuid)

    def test_has_wrapped_model_info_returns_true_after_metadata_is_configured(self):
        entity_model = self.create_entity(name="API Ledger Wrapper Has Info Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-wrapper-has-info",
        )

        ledger_model.configure_for_wrapper_model(BillModel())

        self.assertTrue(ledger_model.has_wrapped_model_info())

    def test_remove_wrapped_model_info_removes_only_wrapped_metadata(self):
        entity_model = self.create_entity(name="API Ledger Wrapper Remove Info Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-wrapper-remove-info",
            additional_info={"preserved": "value"},
        )
        ledger_model.configure_for_wrapper_model(BillModel())

        ledger_model.remove_wrapped_model_info()

        self.assertEqual(ledger_model.additional_info, {"preserved": "value"})

    def test_has_wrapped_model_info_returns_false_after_metadata_removal(self):
        entity_model = self.create_entity(name="API Ledger Wrapper Removed Info Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-wrapper-removed-info",
        )
        ledger_model.configure_for_wrapper_model(BillModel())

        ledger_model.remove_wrapped_model_info()

        self.assertFalse(ledger_model.has_wrapped_model_info())

    def test_get_wrapper_info_exposes_supported_wrapper_model_mapping(self):
        entity_model = self.create_entity(name="API Ledger Wrapper Mapping Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-wrapper-mapping",
        )

        wrapper_info = ledger_model.get_wrapper_info

        self.assertEqual(wrapper_info[BillModel], "billmodel")
        self.assertEqual(wrapper_info[InvoiceModel], "invoicemodel")

    def test_can_delete_is_false_when_wrapped_model_metadata_exists(self):
        entity_model = self.create_entity(name="API Ledger Wrapper Delete Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-wrapper-delete",
        )

        ledger_model.configure_for_wrapper_model(BillModel())

        self.assertFalse(ledger_model.can_delete())
