"""View integration tests for purchase order URLs."""

from django_ledger.models import PurchaseOrderModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class PurchaseOrderViewTests(DjangoLedgerViewTestCase):
    """Purchase order list/detail/update and status actions."""

    def _any_purchase_order(self) -> PurchaseOrderModel:
        po = (
            PurchaseOrderModel.objects.filter(entity=self.get_entity())
            .order_by('uuid')
            .first()
        )
        if po is None:
            self.skipTest('No purchase order in fixture data')
        return po

    def _draft_purchase_order(self) -> PurchaseOrderModel:
        po = (
            PurchaseOrderModel.objects.filter(
                entity=self.get_entity(),
                po_status=PurchaseOrderModel.PO_STATUS_DRAFT,
            )
            .order_by('uuid')
            .first()
        )
        if po is None:
            self.skipTest('No draft purchase order in fixture data')
        return po

    def test_po_list_login_required(self):
        self.assert_login_required(self.reverse_entity('po-list'))

    def test_po_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('po-list'))

    def test_po_list_get_ok(self):
        self.assert_get_ok(self.reverse_entity('po-list'))

    def test_po_detail_login_required(self):
        po = self._any_purchase_order()
        self.assert_login_required(
            self.reverse_entity('po-detail', po_pk=po.uuid),
        )

    def test_po_detail_foreign_entity_forbidden(self):
        po = self._any_purchase_order()
        self.assert_unauthorized_entity(
            self.reverse_foreign('po-detail', po_pk=po.uuid),
        )

    def test_po_detail_get_ok(self):
        po = self._any_purchase_order()
        self.assert_get_ok(self.reverse_entity('po-detail', po_pk=po.uuid))

    def test_po_create_get_ok(self):
        self.assert_get_ok(self.reverse_entity('po-create'))

    def test_po_update_get_ok(self):
        po = self._any_purchase_order()
        self.assert_get_ok(self.reverse_entity('po-update', po_pk=po.uuid))

    def test_po_mark_as_review_action_security(self):
        po = self._draft_purchase_order()
        url = self.reverse_entity('po-action-mark-as-review', po_pk=po.uuid)
        self.assert_login_required(url, method='post')
        self.assert_unauthorized_entity(
            self.reverse_foreign(
                'po-action-mark-as-review',
                po_pk=po.uuid,
            ),
            method='post',
        )

    def test_po_mark_as_review_post_ok(self):
        po = self._draft_purchase_order()
        self.assert_post_ok(
            self.reverse_entity('po-action-mark-as-review', po_pk=po.uuid),
        )

    def test_po_mark_as_review_get_method_not_allowed(self):
        po = self._any_purchase_order()
        self.assert_action_requires_post(
            self.reverse_entity('po-action-mark-as-review', po_pk=po.uuid),
        )
