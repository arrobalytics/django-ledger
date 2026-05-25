from django.core.management.base import BaseCommand, CommandError

from django_ledger.models.entity import EntityModel
from django_ledger_countries.de import vat as vat_module


class Command(BaseCommand):
    help = 'Re-apply active starter accounts for the entity tax regime (after changing tax profile).'

    def add_arguments(self, parser):
        parser.add_argument('--entity', required=True, help='Entity slug')

    def handle(self, *args, **options):
        try:
            entity = EntityModel.objects.get(slug=options['entity'])
        except EntityModel.DoesNotExist as exc:
            raise CommandError(f'Entity not found: {options["entity"]}') from exc

        coa = entity.default_coa
        if coa is None:
            raise CommandError(f'Entity {entity.slug} has no default chart of accounts.')

        try:
            regime = entity.tax_profile.tax_regime
        except Exception as exc:
            raise CommandError(f'Entity {entity.slug} has no tax profile.') from exc

        active_count = vat_module.apply_regime_starter_activation(coa)
        self.stdout.write(
            self.style.SUCCESS(
                f'Tax regime {regime} applied on {entity.slug}: {active_count} active accounts.'
            )
        )
