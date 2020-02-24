from random import choice
from string import ascii_lowercase, digits

from django.db.models.signals import pre_save
from django.utils.text import slugify

from django_ledger.abstracts.ledger import LedgerModelAbstract

LEDGER_ID_CHARS = ascii_lowercase + digits


def generate_ledger_id(length=10):
    return ''.join(choice(LEDGER_ID_CHARS) for _ in range(length))


class LedgerModel(LedgerModelAbstract):
    """
    Ledger Model from Abstract
    """


def ledgermodel_presave(sender, instance, **kwargs):
    if not instance.slug:
        r_id = generate_ledger_id()
        slug = slugify(instance.name)
        instance.slug = f'{slug}-{r_id}'


pre_save.connect(ledgermodel_presave, LedgerModel)
