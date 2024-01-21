"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>
    * Pranav P Tulshyan <ptulshyan77@gmail.com>

A Bank Account refers to the financial institution which holds financial assets for the EntityModel.
A bank account usually holds cash, which is a Current Asset. Transactions may be imported using the open financial
format specification OFX into a staging area for final disposition into the EntityModel ledger.
"""
from typing import Optional
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from django_ledger.models import CreateUpdateMixIn, BankAccountInfoMixIn
from django_ledger.models.utils import lazy_loader

UserModel = get_user_model()


class BankAccountValidationError(ValidationError):
    pass


class BankAccountModelQuerySet(QuerySet):
    """
    A custom defined QuerySet for the BankAccountModel.
    """

    def active(self) -> QuerySet:
        """
        Active bank accounts which can be used to create new transactions.

        Returns
        _______
        BankAccountModelQuerySet
            A filtered BankAccountModelQuerySet of active accounts.
        """
        return self.filter(active=True)

    def hidden(self) -> QuerySet:
        """
        Hidden bank accounts which can be used to create new transactions. but will not show in drop down menus
        in the UI.

        Returns
        _______
        BankAccountModelQuerySet
            A filtered BankAccountModelQuerySet of active accounts.
        """
        return self.filter(hidden=True)


class BankAccountModelManager(models.Manager):
    """
    Custom defined Model Manager for the BankAccountModel.
    """

    def for_user(self, user_model):
        qs = self.get_queryset()
        if user_model.is_superuser:
            return qs
        return qs.filter(
            Q(entity_model__admin=user_model) |
            Q(entity_model__managers__in=[user_model])
        )

    def for_entity(self, entity_slug, user_model) -> BankAccountModelQuerySet:
        """
        Allows only the authorized user to query the BankAccountModel for a given EntityModel.
        This is the recommended initial QuerySet.

        Parameters
        __________
        entity_slug: str or EntityModel
            The entity slug or EntityModel used for filtering the QuerySet.
        user_model
            Logged in and authenticated django UserModel instance.
        """
        qs = self.for_user(user_model)
        if isinstance(entity_slug, lazy_loader.get_entity_model()):
            return qs.filter(
                Q(entity_model=entity_slug)
            )
        return qs.filter(
            Q(entity_model__slug__exact=entity_slug)
        )


class BackAccountModelAbstract(BankAccountInfoMixIn, CreateUpdateMixIn):
    """
    This is the main abstract class which the BankAccountModel database will inherit from.
    The BankAccountModel inherits functionality from the following MixIns:

        1. :func:`BankAccountInfoMixIn <django_ledger.models.mixins.BankAccountInfoMixIn>`
        2. :func:`CreateUpdateMixIn <django_ledger.models.mixins.CreateUpdateMixIn>`


    Attributes
    ----------
    uuid : UUID
        This is a unique primary key generated for the table. The default value of this field is uuid4().
    name: str
        A user defined name for the bank account as a String.
    entity_model: EntityModel
        The EntityModel associated with the BankAccountModel instance.
    cash_account: AccountModel
        The AccountModel associated with the BankAccountModel instance. Must be an account with role ASSET_CA_CASH.
    active: bool
        Determines whether the BackAccountModel instance bank account is active. Defaults to True.
    hidden: bool
        Determines whether the BackAccountModel instance bank account is hidden. Defaults to False.
    """
    REL_NAME_PREFIX = 'bank'

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)

    # todo: rename to account_name?...
    name = models.CharField(max_length=150, null=True, blank=True)
    entity_model = models.ForeignKey('django_ledger.EntityModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_('Entity Model'))
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.RESTRICT,
                                     verbose_name=_('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account')
    active = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    objects = BankAccountModelManager.from_queryset(queryset_class=BankAccountModelQuerySet)()

    def configure(self,
                  entity_slug,
                  user_model: Optional[UserModel],
                  commit: bool = False):

        EntityModel = lazy_loader.get_entity_model()
        if isinstance(entity_slug, str):
            if not user_model:
                raise BankAccountValidationError(_('Must pass user_model when using entity_slug.'))
            entity_model_qs = EntityModel.objects.for_user(user_model=user_model)
            entity_model = get_object_or_404(entity_model_qs, slug__exact=entity_slug)
        elif isinstance(entity_slug, EntityModel):
            entity_model = entity_slug
        else:
            raise BankAccountValidationError('entity_slug must be an instance of str or EntityModel')

        self.entity_model = entity_model
        self.clean()
        if commit:
            self.save(update_fields=[
                'entity_model',
                'updated'
            ])
        return self, entity_model

    def is_active(self):
        return self.active is True

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
        return f'{self.get_account_type_display()} Bank Account: {self.name}'

    def can_activate(self) -> bool:
        return self.active is False

    def can_inactivate(self) -> bool:
        return self.active is True

    def mark_as_active(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        if not self.can_activate():
            if raise_exception:
                raise BankAccountValidationError('Bank Account cannot be activated.')
        self.active = True
        if commit:
            self.save(update_fields=[
                'active',
                'updated'
            ])

    def mark_as_inactive(self, commit: bool = False, raise_exception: bool = True, **kwargs):
        if not self.can_inactivate():
            if raise_exception:
                raise BankAccountValidationError('Bank Account cannot be deactivated.')
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
