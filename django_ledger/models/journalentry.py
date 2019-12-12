from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save

from django_ledger.model_base import load_model_abstract
from django_ledger.settings import DJANGO_LEDGER_SETTINGS

JournalEntryModelAbstract = load_model_abstract(DJANGO_LEDGER_SETTINGS.get('JOURNAL_ENTRY_MODEL_ABSTRACT'))


class JournalEntryModel(JournalEntryModelAbstract):
    """
    Journal Entry Model Base Class From Abstract
    """


def je_presave(sender, instance, *args, **kwargs):
    try:
        instance.clean_fields()
        instance.clean()
    except ValidationError:
        instance.txs.all().delete()
        raise ValidationError('Something went wrong cleaning journal entry ID: {x1}'.format(x1=instance.id))


pre_save.connect(je_presave, sender=JournalEntryModel)
