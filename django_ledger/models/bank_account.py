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


class BankAccountModelManager(models.Manager):
    """
    This model manager is a custome made model manager to act as a interface for the Db queries for the Bank Account Model.
    "for_entity" allows only the authorized user to query the Bank Account model for its entity.
    """

    def for_entity(self, entity_slug: str, user_model):
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

    It inherits the CreateUpdateMixIn and hence create the two field created at and Updated at.

    Below are the fields that are specific to this Bank Account Model.
    @uuid : this is a unique primary key generated for the table. the default value of this fields is set as the unique uuid generated.
    @name: This is the user defined name  of the Account. the maximum length for Name of the ledger allowed is 150
    @account_number: This is the Bank Account number . Only Digits are allowed.
    @routing_number: User defined routing number for the concerned bank account. Also called as 'Routing Transit Number (RTN)' 
    @aba_number: The American Bankers Association Number assigned to each bank.
    @account_type: Each account will have to select from the available choices Checking, Savings or Money Market.
    @cash_account: This is a foreigh key from the man accounts model. It will have all thse account which are marked as Cash Account in the main Coa  
    @active: Determines whether the concerned bank account is active. Any Account can be used only when it is unlocked and Active Default value is set to False i.e Unlocked
    @hidden: Determines whether the concerned bank account is set to hidden. Default value is set to False i.e Not hidden
    @objects: setting the default Model Manager to the BankAccountModelManager


    Some Meta Information: (Additional data points regarding this model that may alter its behavior)

    @abstract: This is a abstract class and will be used through inheritance. Separate implementation can be done for this abstract class.
    [It may also be noted that models are not created for the abstract models, but only for the models which implements the abstract model class]
    @verbose_name: A human readable name for this Model (Also translatable to other languages with django translation> gettext_lazy)
    @unique_together: the concantanation of cash account, account and RTN would remain unique throughout the model i.e database
    @indexes : Index created on different attributes for better db & search queries
    
    

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
