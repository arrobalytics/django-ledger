from django.core.management.base import BaseCommand

from django_ledger.models.entity import EntityModel

from django_ledger_extensions.reminders.service import process_accounting_reminders, seed_default_reminder_rules


class Command(BaseCommand):
    help = 'Send due accounting reminder emails (run daily via cron).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be sent')
        parser.add_argument('--fail-silently', action='store_true', help='Pass through to send_mail')

    def handle(self, *args, **options):
        summary = process_accounting_reminders(
            dry_run=options['dry_run'],
            fail_silently=options['fail_silently'],
        )
        sent = summary.sent_count
        pending = [r for r in summary.results if r.skipped_reason == 'dry_run']
        if options['dry_run']:
            self.stdout.write(f'Would send {len(pending)} reminder(s).')
            for result in pending:
                self.stdout.write(
                    f'  rule={result.rule_id} period={result.period_key} '
                    f'due={result.due_date} → {result.recipient}'
                )
        else:
            self.stdout.write(self.style.SUCCESS(f'Sent {sent} reminder(s).'))
