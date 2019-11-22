from random import randint

from django.db import models
from django.db.models.signals import pre_save
from django.utils.text import slugify

from django_ledger.models.accounts import AccountModel
from django_ledger.models.coa import get_coa_account
from django_ledger.models.mixins.base import CreateUpdateMixIn, SlugNameMixIn
from django_ledger.models.mixins.io import IOMixIn


class LedgerModelManager(models.Manager):

    def posted(self):
        return self.get_queryset().filter(posted=True)


class LedgerModelAbstract(SlugNameMixIn,
                          CreateUpdateMixIn,
                          IOMixIn):
    posted = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               related_name='ledgers')

    objects = LedgerModelManager()

    class Meta:
        abstract = True

    def __str__(self):
        return '{slug}: {name}'.format(name=self.name,
                                       slug=self.slug)

    def get_coa(self):
        return self.entity.coa

    def get_accounts(self):
        return AccountModel.on_coa.available(coa=self.get_coa())

    def get_account(self, code):
        """
        Convenience method to get an account model instance from the ledger entity Chart of Accounts.
        :param code: Account code.
        :return:
        """
        return get_coa_account(coa_model=self.get_coa(),
                               code=code)

    def get_account_balance(self, account_code: str, as_of: str = None):
        return self.get_jes(account=account_code, as_of=as_of)


class LedgerModel(LedgerModelAbstract):
    """
    Final LedgerModel from Abstracts
    """


def ledgermodel_presave(sender, instance, **kwargs):
    if not instance.slug:
        r_int = randint(10000, 99999)
        slug = slugify(instance.name)
        instance.slug = f'{slug}-{r_int}'


pre_save.connect(ledgermodel_presave, LedgerModel)
