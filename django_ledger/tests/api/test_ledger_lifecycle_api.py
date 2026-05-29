"""
High-level API behavior tests for LedgerModel lifecycle transitions.

These tests cover direct public state changes without closing-period, delete,
or signal behavior.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import LedgerModel
from django_ledger.models.entity import EntityModel


class LedgerLifecycleAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_ledger_lifecycle_admin",
            email="api-ledger-lifecycle-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Ledger Lifecycle Entity"):
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
        name="API Ledger Lifecycle Ledger",
        ledger_xid="api-ledger-lifecycle-ledger",
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

    def test_post_commit_false_updates_only_in_memory_state(self):
        entity_model = self.create_entity(name="API Ledger Post Commit False Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-post-commit-false",
            posted=False,
            locked=False,
        )

        ledger_model.post(commit=False)

        self.assertTrue(ledger_model.posted)

        ledger_model.refresh_from_db()
        self.assertFalse(ledger_model.posted)

    def test_post_commit_true_persists_posted_state(self):
        entity_model = self.create_entity(name="API Ledger Post Commit True Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-post-commit-true",
            posted=False,
            locked=False,
        )

        ledger_model.post(commit=True)

        ledger_model.refresh_from_db()
        self.assertTrue(ledger_model.posted)

    def test_unpost_commit_true_persists_unposted_state(self):
        entity_model = self.create_entity(name="API Ledger Unpost Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-unpost",
            posted=True,
            locked=False,
        )

        ledger_model.unpost(commit=True)

        ledger_model.refresh_from_db()
        self.assertFalse(ledger_model.posted)

    def test_lock_commit_true_persists_locked_state(self):
        entity_model = self.create_entity(name="API Ledger Lock Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-lock",
            posted=True,
            locked=False,
        )

        ledger_model.lock(commit=True)

        ledger_model.refresh_from_db()
        self.assertTrue(ledger_model.locked)

    def test_unlock_commit_true_persists_unlocked_state(self):
        entity_model = self.create_entity(name="API Ledger Unlock Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-unlock",
            posted=True,
            locked=True,
        )

        ledger_model.unlock(commit=True)

        ledger_model.refresh_from_db()
        self.assertFalse(ledger_model.locked)

    def test_hide_commit_true_persists_hidden_state(self):
        entity_model = self.create_entity(name="API Ledger Hide Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-hide",
            hidden=False,
        )

        ledger_model.hide(commit=True)

        ledger_model.refresh_from_db()
        self.assertTrue(ledger_model.hidden)

    def test_unhide_commit_true_persists_visible_state(self):
        entity_model = self.create_entity(name="API Ledger Unhide Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-unhide",
            hidden=True,
        )

        ledger_model.unhide(commit=True)

        ledger_model.refresh_from_db()
        self.assertFalse(ledger_model.hidden)

    def test_invalid_transitions_with_raise_exception_false_are_noops(self):
        entity_model = self.create_entity(name="API Ledger Invalid Transition Entity")

        already_posted = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-already-posted",
            posted=True,
            locked=False,
        )
        unposted = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-unposted-transition",
            posted=False,
            locked=False,
        )
        unposted_for_lock = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-unposted-lock",
            posted=False,
            locked=False,
        )
        unlocked = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-unlocked-transition",
            posted=True,
            locked=False,
        )
        hidden = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-hidden-transition",
            hidden=True,
        )
        visible = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-visible-transition",
            hidden=False,
        )

        already_posted.post(commit=True, raise_exception=False)
        unposted.unpost(commit=True, raise_exception=False)
        unposted_for_lock.lock(commit=True, raise_exception=False)
        unlocked.unlock(commit=True, raise_exception=False)
        hidden.hide(commit=True, raise_exception=False)
        visible.unhide(commit=True, raise_exception=False)

        already_posted.refresh_from_db()
        unposted.refresh_from_db()
        unposted_for_lock.refresh_from_db()
        unlocked.refresh_from_db()
        hidden.refresh_from_db()
        visible.refresh_from_db()

        self.assertTrue(already_posted.posted)
        self.assertFalse(unposted.posted)
        self.assertFalse(unposted_for_lock.locked)
        self.assertFalse(unlocked.locked)
        self.assertTrue(hidden.hidden)
        self.assertFalse(visible.hidden)
