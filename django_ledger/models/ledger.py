"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
Pranav P Tulshyan <pranav.tulshyan@gmail.com>

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

"""


"""


def generate_ledger_id(length=10):

    """
    To generate a random 10 characters for generating a unique ledger id



    """

    return ''.join(choice(LEDGER_ID_CHARS) for _ in range(length))


class LedgerModelManager(models.Manager):


    """
    This model Manager will be used as interface through which the database query operations can be provided to the Ledger Model.

    The "for_entity" method will ensure that a particular entity is able to view only their respective ledgers.

    The "posted" method is used to call only the ledgers which are at posted stage.

    """

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


class LedgerModelAbstract(CreateUpdateMixIn, IOMixIn):
    """
        This is the main abstract class which the Ledger database will inherit, and it contains the fields/columns/attributes which the said ledger table will have.

        In addition to the attributes mentioned below, it also has the the fields/columns/attributes mentioned in the
        IO MixIn & the CreateUpdateMixIn. Read about these mixin here.

        Below are the fields specific to the ledger model.

        @uuid : this is a unique primary key generated for the table. the default value of this fields is set as the
        unique uuid generated.

        @name: This is the user defined name  of the Ledger. the maximum length for Name of the ledger allowed is 150

        @entity : A Foreign Key. The values for this columns needs to be chosen from the list of entities which is discussed
        at length in the entity models.

        @posted: By default, the value is set to False. The balances of an ledger is considered in final accounts, only when the ledger is posted.

        @locked:This determines whether any changes can be done in the ledger or not. Before making any update to the ledger, the ledger needs to be unlocked
        Default value is set to False i.e Unlocked

        @hidden: Hides the particular ledger from others. Balances of an hidden ledger is not visible in the final accounts.

        @objects: This object has been created for the purpose of the managing the models and in turn handling the database

        Some Meta Information: (Additional data points regarding this model that may alter its behavior)

        @abstract: This is a abstract class and will be used through inheritance. Separate implementation can be done for this abstract class.
        [It may also be noted that models are not created for the abstract models, but only for the models which implements the abstract model class]

        @verbose_name: A human readable name for this Model (Also translatable to other languages with django translation> gettext_lazy)

        @indexes : Index created on different attributes for better db & search queries

        """


    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=150, null=True, blank=True, verbose_name=_('Ledger Name'))
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               on_delete=models.CASCADE,
                               verbose_name=_('Ledger Entity'))
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

    # pylint: disable=bad-option-value
    def __str__(self):


        # pylint: disable=invalid-str-returned
        return self.name

    def get_absolute_url(self):
        return reverse('django_ledger:ledger-detail',
                       kwargs={
                           # pylint: disable=no-member
                           'entity_slug': self.entity.slug,
                           'ledger_pk': self.uuid
                       })

    def get_update_url(self):
        return reverse('django_ledger:ledger-update',
                       kwargs={
                           # pylint: disable=no-member
                           'entity_slug': self.entity.slug,
                           'ledger_pk': self.uuid
                       })

    def post(self, commit: bool = False):

        """
        Function used for posting a particular ledger

        Each time an ledger is posted, the updated by column is also updated with the current timestamp

        """

        if not self.posted:
            self.posted = True
            if commit:
                self.save(update_fields=[
                    'posted',
                    'updated'
                ])

    def unpost(self, commit: bool = False):

        """
        Function used for un-posting a particular ledger

        Each time an ledger is posted, the updated by column is also updated with the current timestamp

        """


        if self.posted:
            self.posted = False
            if commit:
                self.save(update_fields=[
                    'posted',
                    'updated'
                ])

    def lock(self, commit: bool = False):

        """
           Function used for locking a particular ledger

           Each time an ledger is locked, the updated by column is also updated with the current timestamp

        """

        self.locked = True
        if commit:
            self.save(update_fields=[
                'locked',
                'updated'
            ])

    def unlock(self, commit: bool = False):
        """
           Function used for unlocking a particular ledger.

           Each time an ledger is locked, the updated by column is also updated with the current timestamp

        """


        self.locked = False
        if commit:
            self.save(update_fields=[
                'locked',
                'updated'
            ])


class LedgerModel(LedgerModelAbstract):
    """
    Ledger Model from Abstract
    """