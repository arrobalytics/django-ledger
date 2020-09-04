from random import choices
from string import ascii_lowercase, digits
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Manager, Q
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

from django_ledger.io import IOMixIn
from django_ledger.models.coa import ChartOfAccountModel
from django_ledger.models.mixins import CreateUpdateMixIn, SlugNameMixIn, ContactInfoMixIn

UserModel = get_user_model()

ENTITY_RANDOM_SLUG_SUFFIX = ascii_lowercase + digits


class EntityModelManager(Manager):

    def for_user(self, user_model):
        qs = self.get_queryset()
        return qs.filter(
            Q(admin=user_model) |
            Q(managers__in=[user_model])
        )


class EntityModelAbstract(MPTTModel,
                          SlugNameMixIn,
                          CreateUpdateMixIn,
                          ContactInfoMixIn,
                          IOMixIn):
    parent = TreeForeignKey('self',
                            null=True,
                            blank=True,
                            related_name='children',
                            verbose_name=_('Parent Entity'),
                            on_delete=models.CASCADE)

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=150, verbose_name=_('Entity Name'), null=True, blank=True)
    admin = models.ForeignKey(UserModel, on_delete=models.PROTECT,
                              related_name='admin_of', verbose_name=_('Admin'))
    managers = models.ManyToManyField(UserModel, through='EntityManagementModel',
                                      related_name='managed_by', verbose_name=_('Managers'))

    hidden = models.BooleanField(default=False)
    objects = EntityModelManager()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _('Entity')
        verbose_name_plural = _('Entities')  # idea: can use th django plural function...
        indexes = [
            models.Index(fields=['admin']),
            models.Index(fields=['parent']),
        ]

    class MPTTMeta:
        order_insertion_by = ['created']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('django_ledger:entity-dashboard',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_manage_url(self):
        return reverse('django_ledger:entity-manage',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def clean(self):
        if not self.name:
            raise ValidationError(message=_('Must provide a name for EntityModel'))
        if not self.slug:
            slug = slugify(self.name)
            suffix = ''.join(choices(ENTITY_RANDOM_SLUG_SUFFIX, k=6))
            entity_slug = f'{slug}-{suffix}'
            self.slug = entity_slug

    def save(self, *args, **kwargs):
        # todo: should this be par of pre-save signal?...
        self.clean()
        super().save(*args, **kwargs)
        if not getattr(self, 'coa', None):
            ChartOfAccountModel.objects.create(
                slug=self.slug + '-coa',
                name=self.name + ' CoA',
                entity=self
            )
            self.ledgers.create(
                name=_(f'{self.name} General Ledger'),
                posted=True
            )


class EntityManagementModelAbstract(CreateUpdateMixIn):
    """
    Entity Management Model responsible for manager permissions to read/write.
    """
    PERMISSIONS = [
        ('read', _('Read Permissions')),
        ('write', _('Read/Write Permissions')),
        ('suspended', _('No Permissions'))
    ]

    uuid = models.UUIDField(default=uuid4, editable=False, primary_key=True)
    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_('Entity'),
                               related_name='entity_permissions')
    user = models.ForeignKey(UserModel,
                             on_delete=models.CASCADE,
                             verbose_name=_('Manager'),
                             related_name='entity_permissions')
    permission_level = models.CharField(max_length=10,
                                        default='read',
                                        choices=PERMISSIONS,
                                        verbose_name=_('Permission Level'))

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['entity', 'user']),
            models.Index(fields=['user', 'entity'])
        ]


class EntityModel(EntityModelAbstract):
    """
    Entity Model Base Class From Abstract
    """


class EntityManagementModel(EntityManagementModelAbstract):
    """
    EntityManagement Model Base Class From Abstract
    """
