from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Manager, Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _l

from django_ledger.models.mixins.base import CreateUpdateMixIn, SlugNameMixIn

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

    def for_user(self, user):
        qs = self.get_queryset()
        return qs.filter(
            Q(entity__admin=user) |
            Q(entity__managers__exact=user)
        )


class ChartOfAccountModelAbstract(SlugNameMixIn,
                                  CreateUpdateMixIn):
    entity = models.OneToOneField('django_ledger.EntityModel',
                                  related_name='coa',
                                  verbose_name=_l('Entity'),
                                  on_delete=models.CASCADE)
    locked = models.BooleanField(default=False, verbose_name=_l('Locked'))
    description = models.TextField(verbose_name=_l('CoA Description'), null=True, blank=True)
    objects = ChartOfAccountModelManager()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _l('Chart of Account')
        verbose_name_plural = _l('Chart of Accounts')

    def __str__(self):
        return f'{self.slug}: {self.name}'

    def get_absolute_url(self):
        return reverse('django_ledger:coa-detail',
                       kwargs={
                           'coa_slug': self.slug,
                           'entity_slug': self.entity.slug
                       })

    def get_update_url(self):
        return reverse('django_ledger:coa-update',
                       kwargs={
                           'coa_slug': self.slug,
                           'entity_slug': self.entity.slug
                       })
