from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel
from django_ledger_countries.de.coa import skr03
from django_ledger_countries.de.coa.datev_loader import clear_datev_coa_cache
from django_ledger_countries.de.coa.starter import apply_starter_activation, get_starter_account_codes


class Command(BaseCommand):
    help = 'Load or refresh SKR03 accounts from the configured DATEV CSV for an entity.'

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Insert accounts even when the chart already has non-root accounts.',
        )
        parser.add_argument(
            '--activate-all',
            action='store_true',
            help='Activate every imported account (default: starter set only).',
        )
        parser.add_argument(
            '--deactivate-all',
            action='store_true',
            help='Deactivate every non-root account after import.',
        )

    def handle(self, *args, **options):
        clear_datev_coa_cache()
        skr03.clear_datev_coa_cache()

        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        csv_path = skr03.resolve_csv_path()
        if not csv_path.exists():
            raise CommandError(f'SKR03 CSV not found: {csv_path}')

        coa = entity.default_coa
        if coa is None:
            coa = entity.create_chart_of_accounts(assign_as_default=True, commit=True)

        self.stdout.write(f'Loading SKR03 from {csv_path}')
        entity.populate_default_coa(
            activate_accounts=False,
            force=options['force'],
            coa_model=coa,
        )

        if options['deactivate_all']:
            coa.accountmodel_set.not_coa_root().update(active=False)
            active_count = 0
        elif options['activate_all']:
            active_count = coa.accountmodel_set.not_coa_root().update(active=True)
        else:
            active_count = apply_starter_activation(coa)

        total = coa.accountmodel_set.not_coa_root().count()
        starter = len(get_starter_account_codes())
        self.stdout.write(
            self.style.SUCCESS(
                f'SKR03 sync complete on {entity.slug}: {total} accounts loaded, '
                f'{active_count} active (starter default: {starter}).'
            )
        )
