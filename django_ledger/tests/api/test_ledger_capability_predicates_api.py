"""
High-level API behavior tests for LedgerModel capability predicates.

These tests cover direct action availability predicates and default invalid
transition exceptions without locked-period or signal behavior.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import LedgerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.ledger import LedgerModelValidationError


class LedgerCapabilityPredicatesAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_ledger_capability_admin",
            email="api-ledger-capability-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Ledger Capability Entity"):
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
        name="API Ledger Capability Ledger",
        ledger_xid="api-ledger-capability-ledger",
        posted=False,
        locked=False,
        hidden=False,
    ):
        return LedgerModel.objects.create(
            name=name,
            ledger_xid=ledger_xid,
            entity=entity_model,
            posted=posted,
            locked=locked,
            hidden=hidden,
        )

    def test_can_post_is_true_only_for_unposted_unlocked_ledger(self):
        entity_model = self.create_entity(name="API Ledger Can Post Entity")
        unposted_unlocked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-can-post",
            posted=False,
            locked=False,
        )
        posted_unlocked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-cannot-post-posted",
            posted=True,
            locked=False,
        )
        unposted_locked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-cannot-post-locked",
            posted=False,
            locked=True,
        )

        self.assertTrue(unposted_unlocked.can_post())
        self.assertFalse(posted_unlocked.can_post())
        self.assertFalse(unposted_locked.can_post())

    def test_can_unpost_is_true_only_for_posted_unlocked_ledger(self):
        entity_model = self.create_entity(name="API Ledger Can Unpost Entity")
        posted_unlocked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-can-unpost",
            posted=True,
            locked=False,
        )
        unposted_unlocked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-cannot-unpost-unposted",
            posted=False,
            locked=False,
        )
        posted_locked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-cannot-unpost-locked",
            posted=True,
            locked=True,
        )

        self.assertTrue(posted_unlocked.can_unpost())
        self.assertFalse(unposted_unlocked.can_unpost())
        self.assertFalse(posted_locked.can_unpost())

    def test_can_lock_is_true_only_for_posted_unlocked_ledger(self):
        entity_model = self.create_entity(name="API Ledger Can Lock Entity")
        posted_unlocked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-can-lock",
            posted=True,
            locked=False,
        )
        unposted_unlocked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-cannot-lock-unposted",
            posted=False,
            locked=False,
        )
        posted_locked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-cannot-lock-locked",
            posted=True,
            locked=True,
        )

        self.assertTrue(posted_unlocked.can_lock())
        self.assertFalse(unposted_unlocked.can_lock())
        self.assertFalse(posted_locked.can_lock())

    def test_can_unlock_is_true_only_for_posted_locked_ledger(self):
        entity_model = self.create_entity(name="API Ledger Can Unlock Entity")
        posted_locked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-can-unlock",
            posted=True,
            locked=True,
        )
        posted_unlocked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-cannot-unlock-unlocked",
            posted=True,
            locked=False,
        )
        unposted_locked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-cannot-unlock-unposted",
            posted=False,
            locked=True,
        )

        self.assertTrue(posted_locked.can_unlock())
        self.assertFalse(posted_unlocked.can_unlock())
        self.assertFalse(unposted_locked.can_unlock())

    def test_can_hide_and_can_unhide_reflect_hidden_state(self):
        entity_model = self.create_entity(name="API Ledger Can Hide Entity")
        visible_ledger = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-can-hide",
            hidden=False,
        )
        hidden_ledger = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-can-unhide",
            hidden=True,
        )

        self.assertTrue(visible_ledger.can_hide())
        self.assertFalse(visible_ledger.can_unhide())

        self.assertFalse(hidden_ledger.can_hide())
        self.assertTrue(hidden_ledger.can_unhide())

    def test_invalid_lifecycle_transitions_raise_by_default(self):
        entity_model = self.create_entity(name="API Ledger Invalid Capability Entity")
        already_posted = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-invalid-post",
            posted=True,
            locked=False,
        )
        unposted = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-invalid-unpost",
            posted=False,
            locked=False,
        )
        unposted_for_lock = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-invalid-lock",
            posted=False,
            locked=False,
        )
        unlocked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-invalid-unlock",
            posted=True,
            locked=False,
        )
        hidden = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-invalid-hide",
            hidden=True,
        )
        visible = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-invalid-unhide",
            hidden=False,
        )

        invalid_actions = (
            already_posted.post,
            unposted.unpost,
            unposted_for_lock.lock,
            unlocked.unlock,
            hidden.hide,
            visible.unhide,
        )

        for action in invalid_actions:
            with self.subTest(action=action.__qualname__):
                with self.assertRaises(LedgerModelValidationError):
                    action()
