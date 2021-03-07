"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from random import choice
from string import ascii_lowercase, digits
from uuid import uuid4

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.io import IOMixIn
from django_ledger.models.accounts import AccountModel
from django_ledger.models.coa import get_coa_account
from django_ledger.models.mixins import CreateUpdateMixIn

LEDGER_ID_CHARS = ascii_lowercase + digits


def generate_ledger_id(length=10):
    return ''.join(choice(LEDGER_ID_CHARS) for _ in range(length))


class LedgerModelManager(models.Manager):

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(entity__slug__exact=entity_slug) &
            (
                    Q(entity__admin=user_model) |
                    Q(entity__managers__in=[user_model])
            )
        )

    def posted(self):
        return self.get_queryset().filter(posted=True)


class LedgerModelAbstract(CreateUpdateMixIn,
                          IOMixIn):
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=150, null=True, blank=True, verbose_name=_('Ledger Name'))
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Ledger Entity'),
                               related_name='ledgers')
    posted = models.BooleanField(default=False, verbose_name=_('Posted Ledger'))
    locked = models.BooleanField(default=False, verbose_name=_('Locked Ledger'))
    hidden = models.BooleanField(default=False, verbose_name=_('Hidden Ledger'))

    objects = LedgerModelManager()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Ledger')
        verbose_name_plural = _('Ledgers')
        indexes = [
            models.Index(fields=['entity']),
            models.Index(fields=['entity', 'posted']),
            models.Index(fields=['entity', 'locked']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('django_ledger:ledger-detail',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'ledger_pk': self.uuid
                       })

    def get_update_url(self):
        return reverse('django_ledger:ledger-update',
                       kwargs={
                           'entity_slug': self.entity.slug,
                           'ledger_pk': self.uuid
                       })

    # def get_coa(self):
    #     return self.entity.coa
    #
    # def get_accounts(self):
    #     return AccountModel.on_coa.available(coa=self.get_coa())

    # def get_account(self, code):
    #     """
    #     Convenience method to get an account model instance from the ledger entity Chart of Accounts.
    #     :param code: Account code.
    #     :return:
    #     """
    #     return get_coa_account(coa_model=self.get_coa(),
    #                            code=code)

    # def get_account_balance(self, account_code: str, as_of: str = None):
    #     return self.get_jes(accounts=account_code, to_date=as_of)

    # def clean(self):
    #     if not self.slug:
    #         r_id = generate_ledger_id()
    #         slug = slugify(self.name)
    #         self.slug = f'{slug}-{r_id}'
    #
    # def save(self, *args, **kwargs):
    #     self.clean()
    #     super().save(*args, **kwargs)


class LedgerModel(LedgerModelAbstract):
    """
    Ledger Model from Abstract
    """
