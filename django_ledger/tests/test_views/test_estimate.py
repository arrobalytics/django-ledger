"""View integration tests for customer estimate (estimate) URLs."""

from django_ledger.models import EstimateModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class EstimateViewTests(DjangoLedgerViewTestCase):
    """Customer estimate list/detail/update and status actions."""

    def _draft_estimate(self) -> EstimateModel:
        est = (
            EstimateModel.objects.filter(
                entity=self.get_entity(),
                status=EstimateModel.CONTRACT_STATUS_DRAFT,
            )
            .order_by('uuid')
            .first()
        )
        self.assertIsNotNone(est, 'Fixture must include at least one draft estimate')
        return est

    def test_estimate_list_login_required(self):
        self.assert_login_required(self.reverse_entity('customer-estimate-list'))

    def test_estimate_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('customer-estimate-list'))

    def test_estimate_list_get_ok(self):
        self.assert_get_ok(self.reverse_entity('customer-estimate-list'))

    def test_estimate_detail_login_required(self):
        ce = self._draft_estimate()
        self.assert_login_required(
            self.reverse_entity('customer-estimate-detail', ce_pk=ce.uuid),
        )

    def test_estimate_detail_foreign_entity_forbidden(self):
        ce = self._draft_estimate()
        self.assert_unauthorized_entity(
            self.reverse_foreign('customer-estimate-detail', ce_pk=ce.uuid),
        )

    def test_estimate_detail_get_ok(self):
        ce = self._draft_estimate()
        self.assert_get_ok(
            self.reverse_entity('customer-estimate-detail', ce_pk=ce.uuid),
        )

    def test_estimate_create_get_ok(self):
        self.assert_get_ok(self.reverse_entity('customer-estimate-create'))

    def test_estimate_update_get_ok(self):
        ce = self._draft_estimate()
        self.assert_get_ok(
            self.reverse_entity('customer-estimate-update', ce_pk=ce.uuid),
        )

    def test_estimate_mark_as_review_action_security(self):
        ce = self._draft_estimate()
        url = self.reverse_entity(
            'customer-estimate-action-mark-as-review',
            ce_pk=ce.uuid,
        )
        self.assert_login_required(url, method='post')
        self.assert_unauthorized_entity(
            self.reverse_foreign(
                'customer-estimate-action-mark-as-review',
                ce_pk=ce.uuid,
            ),
            method='post',
        )

    def test_estimate_mark_as_review_post_ok(self):
        ce = self._draft_estimate()
        self.assert_post_ok(
            self.reverse_entity(
                'customer-estimate-action-mark-as-review',
                ce_pk=ce.uuid,
            ),
        )

    def test_estimate_mark_as_review_get_method_not_allowed(self):
        ce = self._draft_estimate()
        self.assert_action_requires_post(
            self.reverse_entity(
                'customer-estimate-action-mark-as-review',
                ce_pk=ce.uuid,
            ),
        )
