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
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CreateUpdateMixIn, BankAccountInfoMixIn
from django_ledger.models.utils import lazy_loader


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
            Q(entity_model__slug__exact=entity_slug) &
            (
                    Q(entity_model__admin=user_model) |
                    Q(entity_model__managers__in=[user_model])
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
    entity_model = models.ForeignKey('django_ledger.EntityModel', on_delete=models.RESTRICT,
                                     verbose_name=_('Entity Model'))
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.RESTRICT,
                                     verbose_name=_('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account',
                                     null=True, blank=True)
    active = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    objects = BankAccountModelManager.from_queryset(queryset_class=BankAccountModelQuerySet)()

    def configure(self,
                  entity_slug,
                  user_model,
                  commit: bool = False):

        EntityModel = lazy_loader.get_entity_model()
        if isinstance(entity_slug, str):
            entity_model_qs = EntityModel.objects.for_user(user_model=user_model)
            entity_model = get_object_or_404(entity_model_qs, slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise ValidationError('entity_slug must be an instance of str or EntityModel')

        self.entity_model = entity_model
        self.clean()
        if commit:
            self.save(update_fields=[
                'entity_model',
                'updated'
            ])
        return self, entity_model

    class Meta:
        abstract = True
        verbose_name = _('Bank Account')
        indexes = [
            models.Index(fields=['account_type']),
            models.Index(fields=['cash_account'])
        ]
        unique_together = [
            ('entity_model', 'account_number'),
            ('entity_model', 'cash_account', 'account_number', 'routing_number')
        ]

    def __str__(self):
        return self.name

    def can_activate(self) -> bool:
        return self.active is False

    def can_inactivate(self) -> bool:
        return self.active is True

    def mark_as_active(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        if not self.can_activate():
            if raise_exception:
                raise ValidationError('Bank Account cannot be activated.')
        self.active = True
        if commit:
            self.save(update_fields=[
                'active',
                'updated'
            ])

    def mark_as_inactive(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        if not self.can_inactivate():
            if raise_exception:
                raise ValidationError('Bank Account cannot be deactivated.')
        self.active = False
        if commit:
            self.save(update_fields=[
                'active',
                'updated'
            ])


class BankAccountModel(BackAccountModelAbstract):
    """
    Base Bank Account Model Implementation
    """
