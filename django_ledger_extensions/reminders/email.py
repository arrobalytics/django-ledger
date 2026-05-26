"""
Send accounting reminder emails.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _

from django_ledger_extensions.reminders.deadlines import ReminderDeadline
from django_ledger_extensions.settings import get_reminder_from_email


def build_reminder_email(
    *,
    entity_name: str,
    entity_slug: str,
    deadline: ReminderDeadline,
    due_date: date,
) -> tuple[str, str]:
    subject = f'[Accounting] {deadline.title} — due {due_date.isoformat()} ({entity_name})'
    lines = [
        f'Entity: {entity_name} ({entity_slug})',
        f'Deadline: {deadline.title}',
        f'Due date: {due_date.isoformat()}',
        '',
        *deadline.body_lines,
        '',
        'This is an automated reminder from django-ledger.',
    ]
    body = '\n'.join(line.replace('<slug>', entity_slug) for line in lines)
    return subject, body


def send_reminder_email(
    *,
    recipient: str,
    entity_name: str,
    entity_slug: str,
    deadline: ReminderDeadline,
    due_date: date,
    fail_silently: bool = False,
) -> int:
    subject, body = build_reminder_email(
        entity_name=entity_name,
        entity_slug=entity_slug,
        deadline=deadline,
        due_date=due_date,
    )
    return send_mail(
        subject=subject,
        message=body,
        from_email=get_reminder_from_email(),
        recipient_list=[recipient],
        fail_silently=fail_silently,
    )
