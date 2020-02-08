from random import randint

from django.db.models.signals import pre_save
from django.utils.text import slugify

from django_ledger.abstracts.ledger import LedgerModelAbstract


class LedgerModel(LedgerModelAbstract):
    """
    Ledger Model from Abstract
    """


def ledgermodel_presave(sender, instance, **kwargs):
    if not instance.slug:
        r_int = randint(10000, 99999)
        slug = slugify(instance.name)
        instance.slug = f'{slug}-{r_int}'


pre_save.connect(ledgermodel_presave, LedgerModel)
