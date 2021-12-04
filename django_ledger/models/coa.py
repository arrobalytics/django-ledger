"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Manager, Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn

UserModel = get_user_model()


def get_coa_account(coa_model, code):
    try:
        qs = coa_model.acc_assignments.available()
        acc_model = qs.get(account__code__iexact=code)
        return acc_model
    except ObjectDoesNotExist:
        raise ValueError(
            'Account {acc} is either not assigned, inactive, locked or non existent for CoA: {coa}'.format(
                acc=code,
                coa=coa_model.__str__()
            ))


def make_account_active(coa_model, account_codes: str or list):
    if isinstance(account_codes, str):
        account_codes = [account_codes]
    qs = coa_model.accounts.all()
    acc = qs.filter(code__in=account_codes)
    acc.update(active=True)


class ChartOfAccountModelManager(Manager):

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(entity__slug__iexact=entity_slug) &
            (
                    Q(entity__admin=user_model) |
                    Q(entity__managers__in=[user_model])
            )
        )


class ChartOfAccountModelAbstract(SlugNameMixIn,
                                  CreateUpdateMixIn):
    """
    Base Chart of Accounts Model Abstract
    """

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.OneToOneField('django_ledger.EntityModel',
                                  related_name='coa',
                                  verbose_name=_('Entity'),
                                  on_delete=models.CASCADE)
    locked = models.BooleanField(default=False, verbose_name=_('Locked'))
    description = models.TextField(verbose_name=_('CoA Description'), null=True, blank=True)
    objects = ChartOfAccountModelManager()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Chart of Account')
        verbose_name_plural = _('Chart of Accounts')
        indexes = [
            models.Index(fields=['entity'])
        ]

    def __str__(self):
        return f'{self.slug}: {self.name}'


class ChartOfAccountModel(ChartOfAccountModelAbstract):
    """
    Base ChartOfAccounts Model
    """
