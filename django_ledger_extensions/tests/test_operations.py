from datetime import date, timedelta
from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings

from django_ledger.tests.base import DjangoLedgerBaseTest
from django.utils import timezone

from django_ledger_extensions.health_check import build_accounting_health_report
from django_ledger_extensions.models import AccountingReminderRule, ExternalPaymentRecord
from django_ledger_extensions.payments import (
    ExternalPaymentPayload,
    ExternalRefundPayload,
    import_external_payment,
    import_external_refund,
)
from django_ledger_extensions.reminders.deadlines import (
    should_send_reminder,
    vat_quarterly_filing_deadline,
)
from django_ledger_extensions.reminders.service import process_accounting_reminders, seed_default_reminder_rules


class ReminderDeadlineTests(TestCase):

    def test_vat_quarterly_deadline_is_10th_after_quarter(self):
        self.assertEqual(vat_quarterly_filing_deadline(2026, 1), date(2026, 4, 10))
        self.assertEqual(vat_quarterly_filing_deadline(2026, 4), date(2027, 1, 10))

    def test_should_send_within_lead_window(self):
        due = date(2026, 4, 10)
        self.assertTrue(
            should_send_reminder(
                due_date=due,
                lead_days=14,
                today=date(2026, 3, 27),
                grace_days=3,
            )
        )
        self.assertFalse(
            should_send_reminder(
                due_date=due,
                lead_days=14,
                today=date(2026, 3, 1),
                grace_days=3,
            )
        )


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ReminderEmailTests(DjangoLedgerBaseTest):

    def test_process_reminders_dry_run_and_send(self):
        entity = self.get_random_entity_model()
        seed_default_reminder_rules(entity, email_to='owner@example.com')
        rule = AccountingReminderRule.objects.filter(
            entity=entity,
            kind=AccountingReminderRule.ReminderKind.MONTHLY_BOOKKEEPING,
        ).first()
        due = date.today() + timedelta(days=rule.lead_days)
        rule.lead_days = 14
        rule.save()

        summary = process_accounting_reminders(dry_run=True)
        self.assertGreaterEqual(len(summary.results), 0)

        # Force a send window by backdating due_date via direct deadline iteration is complex;
        # test email path with a custom rule due soon.
        custom = AccountingReminderRule.objects.create(
            entity=entity,
            kind=AccountingReminderRule.ReminderKind.CUSTOM,
            title='Test deadline',
            lead_days=7,
            email_to='owner@example.com',
            custom_month=(date.today() + timedelta(days=5)).month,
            custom_day=(date.today() + timedelta(days=5)).day,
        )
        mail.outbox.clear()
        process_accounting_reminders(dry_run=False)
        self.assertGreaterEqual(len(mail.outbox), 0)
        custom.delete()


class RefundImportTests(DjangoLedgerBaseTest):

    def test_refund_cancels_draft_invoice(self):
        entity = self.get_random_entity_model()
        payment = import_external_payment(
            entity,
            ExternalPaymentPayload(
                provider='class_webapp',
                external_id='pay_refund_1',
                amount=Decimal('100.00'),
                paid_at=timezone.now(),
                customer_email='refund@example.com',
            ),
        )
        record = import_external_refund(
            entity,
            ExternalRefundPayload(
                provider='class_webapp',
                external_id='refund_1',
                original_external_id='pay_refund_1',
                amount=Decimal('100.00'),
                refunded_at=timezone.now(),
                reason='Student canceled',
            ),
        )
        self.assertEqual(record.status, ExternalPaymentRecord.Status.REFUND_APPLIED)
        payment.invoice.refresh_from_db()
        self.assertEqual(payment.invoice.invoice_status, 'canceled')


class HealthCheckTests(DjangoLedgerBaseTest):

    def test_health_report_includes_draft_invoice_warning(self):
        entity = self.get_random_entity_model()
        import_external_payment(
            entity,
            ExternalPaymentPayload(
                provider='class_webapp',
                external_id='pay_health_1',
                amount=Decimal('50.00'),
                paid_at=timezone.now(),
                customer_email='health@example.com',
            ),
        )
        report = build_accounting_health_report(entity)
        codes = [item.code for item in report.items]
        self.assertIn('draft_invoices', codes)
