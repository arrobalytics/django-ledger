"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import int_list_validator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CreateUpdateMixIn
from django_ledger.models.utils import LazyLoader

lazy_loader = LazyLoader()


class BankAccountModelManager(models.Manager):

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(ledger__entity__slug__exact=entity_slug) &
            (
                    Q(ledger__entity__admin=user_model) |
                    Q(ledger__entity__managers__in=[user_model])
            )
        )


class BackAccountModelAbstract(CreateUpdateMixIn):
    REL_NAME_PREFIX = 'bank'
    ACCOUNT_TYPES = [
        ('checking', _('Checking')),
        ('savings', _('Savings')),
        ('money_mkt', _('Money Market')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=150, null=True, blank=True)
    account_number = models.CharField(max_length=30, null=True, blank=True,
                                      validators=[
                                          int_list_validator(sep='', message=_('Only digits allowed'))
                                      ])
    routing_number = models.CharField(max_length=30, null=True, blank=True,
                                      validators=[
                                          int_list_validator(sep='', message=_('Only digits allowed'))
                                      ])
    aba_number = models.CharField(max_length=30, null=True, blank=True)
    account_type = models.CharField(choices=ACCOUNT_TYPES, max_length=10)
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account',
                                     null=True, blank=True)
    ledger = models.OneToOneField('django_ledger.LedgerModel',
                                  editable=False,
                                  verbose_name=_('Ledger'),
                                  on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    hidden = models.BooleanField(default=False)
    objects = BankAccountModelManager()

    def configure(self,
                  entity_slug,
                  user_model,
                  posted_ledger: bool = True):
        EntityModel = lazy_loader.get_entity_model()
        if isinstance(entity_slug, str):
            entity_model = EntityModel.objects.for_user(
                user_model=user_model).get(
                slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise ValidationError('entity_slug must be an instance of str or EntityModel')

        LedgerModel = lazy_loader.get_ledger_model()
        acc_number = self.account_number
        ledger_model = LedgerModel.objects.create(
            entity=entity_model,
            posted=posted_ledger,
            # pylint: disable=unsubscriptable-object
            name=f'Bank Account {"***" + acc_number[-4:]}'
        )
        ledger_model.clean()
        self.ledger = ledger_model
        return self

    class Meta:
        abstract = True
        verbose_name = _('Bank Account')
        indexes = [
            models.Index(fields=['ledger']),
            models.Index(fields=['account_type']),
            models.Index(fields=['cash_account', 'account_type'])
        ]
        unique_together = [
            ('cash_account', 'account_number', 'routing_number')
        ]

    # pylint: disable=invalid-str-returned
    def __str__(self):
        # pylint: disable=bad-option-value
        return self.name


class BankAccountModel(BackAccountModelAbstract):
    """
    Base Bank Account Model
    """
