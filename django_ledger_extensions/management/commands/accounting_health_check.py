import json

from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel

from django_ledger_extensions.health_check import build_accounting_health_report, format_health_report


class Command(BaseCommand):
    help = 'Report open accounting hygiene issues (draft invoices, inbox, bank matches, …).'

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')
        parser.add_argument('--json', action='store_true', help='Output JSON')

    def handle(self, *args, **options):
        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        report = build_accounting_health_report(entity)
        if options['json']:
            self.stdout.write(json.dumps(report.to_dict(), indent=2))
        else:
            self.stdout.write(format_health_report(report))
