"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
Pranav P Tulshyan <ptulshyan77@gmail.com>
"""

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CreateUpdateMixIn, BankAccountInfoMixIn
from django_ledger.models.utils import LazyLoader

lazy_loader = LazyLoader()


class BankAccountModelQuerySet(models.QuerySet):
    """
    Base BankAccountModel QuerySet.
    """


class BankAccountModelManager(models.Manager):
    """
    This model manager acts as an interface for the Db queries for the Bank Account Model.
    """

    def for_entity(self, entity_slug: str, user_model):
        """
        Allows only the authorized user to query the BankAccountModel for a given EntityModel.
        @param entity_slug: Entity slug as a string.
        @param user_model: Current Django User Model
        @return: A Filtered QuerySet
        """
        qs = self.get_queryset()
        return qs.filter(
            Q(ledger__entity__slug__exact=entity_slug) &
            (
                    Q(ledger__entity__admin=user_model) |
                    Q(ledger__entity__managers__in=[user_model])
            )
        )


class BackAccountModelAbstract(BankAccountInfoMixIn, CreateUpdateMixIn):
    """
    This is an abstract base model for the Bank Account Model.

    It inherits from BankAccountInfoMixIn and CreateUpdateMixIn.

    Below are the fields that are specific to this Bank Account Model.

    @uuid: This is a unique primary key generated for the table. the default value of this field is uuid4().
    @name: This is the user defined name  of the Account. The maximum name length allowed is 150 characters.
    @cash_account: This is a foreign key from the AccountsModel. Must be a Cash Account in the main Code of Accounts.
    @active: Determines whether the concerned bank account is active. Default value is True.
    @hidden: Determines whether the concerned bank account is set to hidden. Default value is set to False.
    """
    REL_NAME_PREFIX = 'bank'

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=150, null=True, blank=True)
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
    objects = BankAccountModelManager.from_queryset(queryset_class=BankAccountModelQuerySet)()

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
    Base Bank Account Model Implementation
    """
