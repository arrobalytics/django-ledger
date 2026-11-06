"""View integration tests for journal entry URLs."""

from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class JournalEntryViewTests(DjangoLedgerViewTestCase):
    """Journal entry list/detail/txs/update/delete and mark-as-* actions."""

    def test_je_list_login_required(self):
        ledger = self.get_random_ledger(entity_model=self.get_entity())
        self.assert_login_required(
            self.reverse_entity('je-list', ledger_pk=ledger.uuid),
        )

    def test_je_list_foreign_entity_forbidden(self):
        ledger = self.get_random_ledger(entity_model=self.get_entity())
        self.assert_unauthorized_entity(
            self.reverse_foreign('je-list', ledger_pk=ledger.uuid),
        )

    def test_je_list_get_ok(self):
        ledger = self.get_random_ledger(entity_model=self.get_entity())
        self.assert_get_ok(self.reverse_entity('je-list', ledger_pk=ledger.uuid))

    def test_je_detail_login_required(self):
        entity = self.get_entity()
        ledger = self.get_random_ledger(entity_model=entity)
        je = self.get_random_je(entity_model=entity, ledger_model=ledger)
        self.assert_login_required(
            self.reverse_entity('je-detail', ledger_pk=ledger.uuid, je_pk=je.uuid),
        )

    def test_je_detail_foreign_entity_forbidden(self):
        entity = self.get_entity()
        ledger = self.get_random_ledger(entity_model=entity)
        je = self.get_random_je(entity_model=entity, ledger_model=ledger)
        self.assert_unauthorized_entity(
            self.reverse_foreign(
                'je-detail',
                ledger_pk=ledger.uuid,
                je_pk=je.uuid,
            ),
        )

    def test_je_detail_and_txs_get_ok(self):
        entity = self.get_entity()
        ledger = self.get_random_ledger(entity_model=entity)
        je = self.get_random_je(entity_model=entity, ledger_model=ledger)
        self.assert_get_ok(
            self.reverse_entity('je-detail', ledger_pk=ledger.uuid, je_pk=je.uuid),
        )
        self.assert_get_ok(
            self.reverse_entity(
                'je-detail-txs',
                ledger_pk=ledger.uuid,
                je_pk=je.uuid,
            ),
        )

    def test_je_create_update_delete_get_ok(self):
        entity = self.get_entity()
        ledger = self.get_random_ledger(entity_model=entity)
        je = self.get_random_je(entity_model=entity, ledger_model=ledger)
        self.assert_get_ok(self.reverse_entity('je-create', ledger_pk=ledger.uuid))
        self.assert_get_ok(
            self.reverse_entity('je-update', ledger_pk=ledger.uuid, je_pk=je.uuid),
        )
        self.assert_get_ok(
            self.reverse_entity('je-delete', ledger_pk=ledger.uuid, je_pk=je.uuid),
        )

    def test_je_mark_as_locked_action_security(self):
        entity = self.get_entity()
        ledger = self.get_random_ledger(entity_model=entity)
        je = self.get_random_je(entity_model=entity, ledger_model=ledger)
        url = self.reverse_entity(
            'je-mark-as-locked',
            ledger_pk=ledger.uuid,
            je_pk=je.uuid,
        )
        self.assert_login_required(url, method='post')
        self.assert_unauthorized_entity(
            self.reverse_foreign(
                'je-mark-as-locked',
                ledger_pk=ledger.uuid,
                je_pk=je.uuid,
            ),
            method='post',
        )

    def test_je_mark_as_locked_post_ok(self):
        entity = self.get_entity()
        ledger = self.get_random_ledger(entity_model=entity)
        je = self.get_random_je(entity_model=entity, ledger_model=ledger)
        self.assert_post_ok(
            self.reverse_entity(
                'je-mark-as-locked',
                ledger_pk=ledger.uuid,
                je_pk=je.uuid,
            ),
        )

    def test_je_mark_as_locked_get_method_not_allowed(self):
        entity = self.get_entity()
        ledger = self.get_random_ledger(entity_model=entity)
        je = self.get_random_je(entity_model=entity, ledger_model=ledger)
        self.assert_action_requires_post(
            self.reverse_entity(
                'je-mark-as-locked',
                ledger_pk=ledger.uuid,
                je_pk=je.uuid,
            ),
        )
