"""View integration tests for entity unit URLs."""

from django_ledger.models import EntityUnitModel
from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class EntityUnitViewTests(DjangoLedgerViewTestCase):
    """Unit list/detail for an entity."""

    def _unit_slug(self) -> str:
        unit = (
            EntityUnitModel.objects.filter(entity=self.get_entity())
            .order_by('uuid')
            .first()
        )
        self.assertIsNotNone(unit, 'Fixture must create at least one entity unit')
        return unit.slug

    def test_unit_list_login_required(self):
        self.assert_login_required(self.reverse_entity('unit-list'))

    def test_unit_list_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(self.reverse_foreign('unit-list'))

    def test_unit_list_get_ok(self):
        self.assert_get_ok(self.reverse_entity('unit-list'))

    def test_unit_detail_login_required(self):
        self.assert_login_required(
            self.reverse_entity('unit-detail', unit_slug=self._unit_slug()),
        )

    def test_unit_detail_foreign_entity_forbidden(self):
        self.assert_unauthorized_entity(
            self.reverse_foreign('unit-detail', unit_slug=self._unit_slug()),
        )

    def test_unit_detail_get_ok(self):
        self.assert_get_ok(
            self.reverse_entity('unit-detail', unit_slug=self._unit_slug()),
        )

    def test_unit_create_get_ok(self):
        self.assert_get_ok(self.reverse_entity('unit-create'))

    def test_unit_update_get_ok(self):
        self.assert_get_ok(
            self.reverse_entity('unit-update', unit_slug=self._unit_slug()),
        )
