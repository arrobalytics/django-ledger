from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel

from django_ledger_extensions.reminders.service import seed_default_reminder_rules


class Command(BaseCommand):
    help = 'Create default German UG accounting reminder rules for an entity.'

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')
        parser.add_argument('--email', default='', help='Override recipient email')

    def handle(self, *args, **options):
        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        created = seed_default_reminder_rules(entity, email_to=options['email'])
        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded {len(created)} new reminder rule(s) for {entity.slug}. '
                f'Run send_accounting_reminders daily via cron.'
            )
        )
