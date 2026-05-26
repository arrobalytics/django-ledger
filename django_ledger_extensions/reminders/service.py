"""
Process due accounting reminders (call daily from cron).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from django_ledger_extensions.models import (
    AccountingReminderLog,
    AccountingReminderRule,
    EntityTaxProfile,
)
from django_ledger_extensions.reminders.deadlines import iter_deadlines_for_rule, should_send_reminder
from django_ledger_extensions.reminders.email import send_reminder_email
from django_ledger_extensions.settings import get_extension_setting


@dataclass
class ReminderSendResult:
    rule_id: str
    period_key: str
    due_date: date
    recipient: str
    sent: bool
    skipped_reason: str = ''


@dataclass
class ReminderRunSummary:
    results: List[ReminderSendResult] = field(default_factory=list)

    @property
    def sent_count(self) -> int:
        return sum(1 for r in self.results if r.sent)


def _recipient_for_rule(rule: AccountingReminderRule) -> Optional[str]:
    if rule.email_to:
        return rule.email_to
    admin = getattr(rule.entity, 'admin', None)
    if admin and admin.email:
        return admin.email
    return None


def _rule_applies_to_entity(rule: AccountingReminderRule) -> bool:
    profile = getattr(rule.entity, 'tax_profile', None)
    if profile is None:
        try:
            profile = rule.entity.tax_profile
        except EntityTaxProfile.DoesNotExist:
            profile = None

    regime = profile.tax_regime if profile else EntityTaxProfile.TaxRegime.EXEMPT

    if rule.kind == AccountingReminderRule.ReminderKind.VAT_QUARTERLY_FILING:
        return regime == EntityTaxProfile.TaxRegime.STANDARD
    if rule.kind == AccountingReminderRule.ReminderKind.KLEINUNTERNEHMER_QUARTERLY:
        return regime == EntityTaxProfile.TaxRegime.SMALL_BUSINESS
    return True


def process_accounting_reminders(
    *,
    reference: Optional[date] = None,
    dry_run: bool = False,
    fail_silently: bool = False,
) -> ReminderRunSummary:
    reference = reference or date.today()
    grace_days = int(get_extension_setting('REMINDER_GRACE_DAYS'))
    summary = ReminderRunSummary()

    rules = (
        AccountingReminderRule.objects.filter(is_active=True)
        .select_related('entity', 'entity__admin')
    )
    for rule in rules:
        if not _rule_applies_to_entity(rule):
            continue

        recipient = _recipient_for_rule(rule)
        if not recipient:
            continue

        entity = rule.entity
        for deadline in iter_deadlines_for_rule(rule, reference=reference):
            if AccountingReminderLog.objects.filter(rule=rule, period_key=deadline.period_key).exists():
                summary.results.append(
                    ReminderSendResult(
                        rule_id=str(rule.pk),
                        period_key=deadline.period_key,
                        due_date=deadline.due_date,
                        recipient=recipient,
                        sent=False,
                        skipped_reason='already_sent',
                    )
                )
                continue

            if not should_send_reminder(
                due_date=deadline.due_date,
                lead_days=rule.lead_days,
                today=reference,
                grace_days=grace_days,
            ):
                continue

            if dry_run:
                summary.results.append(
                    ReminderSendResult(
                        rule_id=str(rule.pk),
                        period_key=deadline.period_key,
                        due_date=deadline.due_date,
                        recipient=recipient,
                        sent=False,
                        skipped_reason='dry_run',
                    )
                )
                continue

            send_reminder_email(
                recipient=recipient,
                entity_name=entity.name,
                entity_slug=entity.slug,
                deadline=deadline,
                due_date=deadline.due_date,
                fail_silently=fail_silently,
            )
            AccountingReminderLog.objects.create(
                rule=rule,
                period_key=deadline.period_key,
                due_date=deadline.due_date,
            )
            summary.results.append(
                ReminderSendResult(
                    rule_id=str(rule.pk),
                    period_key=deadline.period_key,
                    due_date=deadline.due_date,
                    recipient=recipient,
                    sent=True,
                )
            )

    return summary


def seed_default_reminder_rules(entity, *, email_to: str = '') -> List[AccountingReminderRule]:
    """Create default German UG reminder rules for an entity (idempotent)."""
    defaults = get_extension_setting('REMINDER_DEFAULT_LEAD_DAYS')
    created: List[AccountingReminderRule] = []
    specs = [
        (AccountingReminderRule.ReminderKind.VAT_QUARTERLY_FILING, 'USt-Voranmeldung'),
        (AccountingReminderRule.ReminderKind.MONTHLY_BOOKKEEPING, 'Monthly bookkeeping'),
        (AccountingReminderRule.ReminderKind.KLEINUNTERNEHMER_QUARTERLY, 'Kleinunternehmer turnover'),
        (AccountingReminderRule.ReminderKind.YEAR_END_HANDOFF, 'Year-end Steuerberater handoff'),
    ]
    for kind, title in specs:
        rule, was_created = AccountingReminderRule.objects.get_or_create(
            entity=entity,
            kind=kind,
            defaults={
                'title': title,
                'lead_days': defaults,
                'email_to': email_to,
                'is_active': True,
            },
        )
        if was_created:
            created.append(rule)
    return created
