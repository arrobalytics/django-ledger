from django.core.management.base import BaseCommand, CommandError

from django.contrib.contenttypes.models import ContentType
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import lazy_loader
from django_ledger_extensions.documents import link_inbox_item_to_object
from django_ledger_extensions.models import DocumentInboxItem


class Command(BaseCommand):
    help = 'Link a document inbox item to an invoice, bill, or journal entry.'

    def add_arguments(self, parser):
        parser.add_argument('--inbox', required=True, help='DocumentInboxItem UUID')
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument('--invoice', help='Invoice UUID')
        target.add_argument('--bill', help='Bill UUID')
        target.add_argument('--journal-entry', dest='journal_entry', help='Journal entry UUID')

    def handle(self, *args, **options):
        try:
            inbox = DocumentInboxItem.objects.get(uuid=options['inbox'])
        except DocumentInboxItem.DoesNotExist as exc:
            raise CommandError(f'Inbox item not found: {options["inbox"]}') from exc

        if options.get('invoice'):
            model = lazy_loader.get_invoice_model()
            object_id = options['invoice']
        elif options.get('bill'):
            model = lazy_loader.get_bill_model()
            object_id = options['bill']
        else:
            model = lazy_loader.get_journal_entry_model()
            object_id = options['journal_entry']

        try:
            target = model.objects.get(uuid=object_id)
        except model.DoesNotExist as exc:
            raise CommandError(f'Target not found: {object_id}') from exc

        doc = link_inbox_item_to_object(inbox, target)
        self.stdout.write(
            self.style.SUCCESS(
                f'Linked inbox {inbox.uuid} → {ContentType.objects.get_for_model(target).model} '
                f'{target.pk} (supporting document {doc.uuid}).'
            )
        )
