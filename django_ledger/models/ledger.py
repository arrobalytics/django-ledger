"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
Miguel Sanda <msanda@arrobalytics.com>
"""

from string import ascii_lowercase, digits
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_ledger.io import IOMixIn
from django_ledger.models import lazy_loader
from django_ledger.models.mixins import CreateUpdateMixIn

LEDGER_ID_CHARS = ascii_lowercase + digits


class LedgerModelValidationError(ValidationError):
    pass


class LedgerModelQuerySet(models.QuerySet):
    """
    Custom defined LedgerModel QuerySet.
    """


class LedgerModelManager(models.Manager):

    def for_entity(self, entity_slug, user_model):
        qs = self.get_queryset()
        if isinstance(entity_slug, lazy_loader.get_entity_model()):
            return qs.filter(
                Q(entity=entity_slug) &
                (
                        Q(entity__admin=user_model) |
                        Q(entity__managers__in=[user_model])
                )
            )
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
    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=150, null=True, blank=True, verbose_name=_('Ledger Name'))
    entity = models.ForeignKey('django_ledger.EntityModel',
                               editable=False,
                               on_delete=models.CASCADE,
                               verbose_name=_('Ledger Entity'))
    posted = models.BooleanField(default=False, verbose_name=_('Posted Ledger'))
    locked = models.BooleanField(default=False, verbose_name=_('Locked Ledger'))
    hidden = models.BooleanField(default=False, verbose_name=_('Hidden Ledger'))

    objects = LedgerModelManager.from_queryset(queryset_class=LedgerModelQuerySet)()

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

    def is_posted(self):
        return self.posted is True

    def is_locked(self):
        return self.locked is True

    def is_hidden(self):
        return self.hidden is True

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
        if not self.posted:
            self.posted = True
            if commit:
                self.save(update_fields=[
                    'posted',
                    'updated'
                ])

    def unpost(self, commit: bool = False):
        if self.posted:
            self.posted = False
            if commit:
                self.save(update_fields=[
                    'posted',
                    'updated'
                ])

    def lock(self, commit: bool = False):
        self.locked = True
        if commit:
            self.save(update_fields=[
                'locked',
                'updated'
            ])

    def unlock(self, commit: bool = False):
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
