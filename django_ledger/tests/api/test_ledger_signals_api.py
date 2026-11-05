"""
Smoke tests for LedgerModel lifecycle signals.

These tests verify that public lifecycle methods emit their corresponding
signals without asserting unrelated payload details.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models import LedgerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.signals import (
    ledger_hidden,
    ledger_locked,
    ledger_posted,
    ledger_unhidden,
    ledger_unlocked,
    ledger_unposted,
)


class LedgerSignalsAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_ledger_signals_admin",
            email="api-ledger-signals-admin@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(self, *, name="API Ledger Signals Entity"):
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
        name="API Ledger Signals Ledger",
        ledger_xid="api-ledger-signals-ledger",
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

    def collect_signal_calls(self, signal):
        calls = []
        dispatch_uid = f"{self.id()}-{id(signal)}"

        def receiver(sender, **kwargs):
            calls.append(kwargs)

        signal.connect(
            receiver,
            sender=LedgerModel,
            weak=False,
            dispatch_uid=dispatch_uid,
        )
        self.addCleanup(
            signal.disconnect,
            sender=LedgerModel,
            dispatch_uid=dispatch_uid,
        )
        return calls

    def assert_signal_received_once(self, calls, ledger_model, *, commit):
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["instance"], ledger_model)
        self.assertEqual(calls[0]["commited"], commit)

    def test_post_emits_ledger_posted_signal(self):
        entity_model = self.create_entity(name="API Ledger Posted Signal Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-posted-signal",
            posted=False,
            locked=False,
        )
        calls = self.collect_signal_calls(ledger_posted)

        ledger_model.post(commit=True)

        self.assert_signal_received_once(calls, ledger_model, commit=True)

    def test_unpost_emits_ledger_unposted_signal(self):
        entity_model = self.create_entity(name="API Ledger Unposted Signal Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-unposted-signal",
            posted=True,
            locked=False,
        )
        calls = self.collect_signal_calls(ledger_unposted)

        ledger_model.unpost(commit=True)

        self.assert_signal_received_once(calls, ledger_model, commit=True)

    def test_lock_emits_ledger_locked_signal(self):
        entity_model = self.create_entity(name="API Ledger Locked Signal Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-locked-signal",
            posted=True,
            locked=False,
        )
        calls = self.collect_signal_calls(ledger_locked)

        ledger_model.lock(commit=True)

        self.assert_signal_received_once(calls, ledger_model, commit=True)

    def test_unlock_emits_ledger_unlocked_signal(self):
        entity_model = self.create_entity(name="API Ledger Unlocked Signal Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-unlocked-signal",
            posted=True,
            locked=True,
        )
        calls = self.collect_signal_calls(ledger_unlocked)

        ledger_model.unlock(commit=True)

        self.assert_signal_received_once(calls, ledger_model, commit=True)

    def test_hide_emits_ledger_hidden_signal(self):
        entity_model = self.create_entity(name="API Ledger Hidden Signal Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-hidden-signal",
            hidden=False,
        )
        calls = self.collect_signal_calls(ledger_hidden)

        ledger_model.hide(commit=True)

        self.assert_signal_received_once(calls, ledger_model, commit=True)

    def test_unhide_emits_ledger_unhidden_signal(self):
        entity_model = self.create_entity(name="API Ledger Unhidden Signal Entity")
        ledger_model = self.create_ledger(
            entity_model,
            ledger_xid="api-ledger-unhidden-signal",
            hidden=True,
        )
        calls = self.collect_signal_calls(ledger_unhidden)

        ledger_model.unhide(commit=True)

        self.assert_signal_received_once(calls, ledger_model, commit=True)
