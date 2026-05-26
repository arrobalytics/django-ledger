from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel

from django_ledger_extensions.steuerberater_export import write_steuerberater_bundle


class Command(BaseCommand):
    help = 'Export JSON + CSV bundle for Steuerberater (posted JEs, Beleg index, VAT summary).'

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')
        parser.add_argument('--year', type=int, required=True, help='Calendar year')
        parser.add_argument('--month', type=int, help='Optional calendar month (1–12)')
        parser.add_argument(
            '--output-dir',
            default='./steuerberater-export',
            help='Directory for export files',
        )

    def handle(self, *args, **options):
        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        month = options.get('month')
        if month is not None and not 1 <= month <= 12:
            raise CommandError('--month must be 1–12')

        path = write_steuerberater_bundle(
            entity,
            options['output_dir'],
            year=options['year'],
            month=month,
        )
        self.stdout.write(self.style.SUCCESS(f'Export written to {path.parent}/'))
