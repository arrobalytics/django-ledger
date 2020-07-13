from random import randint
from uuid import uuid4

from django.core.validators import int_list_validator
from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn


class BankAccountModelManager(models.Manager):

    def for_entity(self, entity_slug: str, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(ledger__entity__slug__iexact=entity_slug) &
            (
                    Q(ledger__entity__admin=user_model) |
                    Q(ledger__entity__managers__in=[user_model])
            )
        )


class BackAccountModelAbstract(SlugNameMixIn, CreateUpdateMixIn):
    REL_NAME_PREFIX = 'bank'
    ACCOUNT_TYPES = [
        ('checking', _('Checking')),
        ('savings', _('Savings')),
        ('money_mkt', _('Money Market')),
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    account_number = models.CharField(max_length=30, null=True, blank=True, validators=[
        int_list_validator(sep='', message=_('Only digits allowed'))
    ])
    routing_number = models.CharField(max_length=30, null=True, blank=True, validators=[
        int_list_validator(sep='', message=_('Only digits allowed'))
    ])
    aba_number = models.CharField(max_length=30, null=True, blank=True)
    account_type = models.CharField(choices=ACCOUNT_TYPES, max_length=10)
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account')
    ledger = models.OneToOneField('django_ledger.LedgerModel',
                                  verbose_name=_('Ledger'),
                                  on_delete=models.CASCADE)

    objects = BankAccountModelManager()

    def clean(self):
        if not self.slug:
            slug = slugify(self.name)
            ri = randint(100000, 999999)
            entity_slug = f'{slug}-{ri}-{self.account_number[-4:]}'
            self.slug = entity_slug

    class Meta:
        abstract = True
        verbose_name = _('Bank Account')
        indexes = [
            models.Index(fields=['ledger']),
            models.Index(fields=['cash_account', 'account_type'])
        ]
        unique_together = [
            ('cash_account', 'account_number', 'routing_number')
        ]


class BankAccountModel(BackAccountModelAbstract):
    """
    Base Bank Account Model
    """
