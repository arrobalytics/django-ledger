from random import randint

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Manager, Q
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _l
from mptt.models import MPTTModel, TreeForeignKey

from django_ledger.abstracts.mixins.base import CreateUpdateMixIn, SlugNameMixIn
from django_ledger.io import IOMixIn
from django_ledger.models import ChartOfAccountModel

UserModel = get_user_model()


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
                          IOMixIn):
    # todo: add company logo field....?
    admin = models.ForeignKey(UserModel, on_delete=models.PROTECT,
                              related_name='admin_of', verbose_name=_l('Admin'))
    managers = models.ManyToManyField(UserModel, through='EntityManagementModel',
                                      related_name='managed_by', verbose_name=_l('Managers'))
    parent = TreeForeignKey('self',
                            null=True,
                            blank=True,
                            related_name='children',
                            verbose_name=_l('Parent'),
                            db_index=True,
                            on_delete=models.CASCADE)

    # todo: can use the mixin???...
    address_1 = models.CharField(max_length=70, null=True, blank=True, verbose_name=_l('Company Address 1'))
    address_2 = models.CharField(max_length=70, null=True, blank=True, verbose_name=_l('Company Address 2'))
    email = models.EmailField(null=True, blank=True, verbose_name=_l('Email'))
    website = models.URLField(null=True, blank=True, verbose_name=_l('Website'))
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name=_l('Phone Number'))

    hidden = models.BooleanField(default=False)
    objects = EntityModelManager()

    class Meta:
        abstract = True
        ordering = ['-created']
        verbose_name = _l('Entity')
        verbose_name_plural = _l('Entities')  # idea: can use th django plural function...

    class MPTTMeta:
        order_insertion_by = ['created']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('django_ledger:entity-detail',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_update_url(self):
        return reverse('django_ledger:entity-update',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_bs_url(self):
        return reverse('django_ledger:entity-bs',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_ic_url(self):
        return reverse('django_ledger:entity-ic',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def get_ledgers_url(self):
        return reverse('django_ledger:ledger-list',
                       kwargs={
                           'entity_slug': self.slug
                       })

    def clean(self):
        if not self.name:
            raise ValidationError(message=_('Must provide a name for EntityModel'))
        if not self.slug:
            slug = slugify(self.name)
            ri = randint(100000, 999999)
            entity_slug = f'{slug}-{ri}'
            self.slug = entity_slug
        if not self.id:
            self.CREATE_GL_FLAG = True

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        if not getattr(self, 'coa', None):
            ChartOfAccountModel.objects.create(
                slug=self.slug + '-coa',
                name=self.name + ' CoA',
                entity=self
            )
            self.ledgers.create(
                name=_('General Ledger'),
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

    entity = models.ForeignKey('django_ledger.EntityModel',
                               on_delete=models.CASCADE,
                               verbose_name=_l('Entity'),
                               related_name='entity_permissions')
    user = models.ForeignKey(UserModel,
                             on_delete=models.CASCADE,
                             verbose_name=_l('Manager'),
                             related_name='entity_permissions')
    permission_level = models.CharField(max_length=10,
                                        default='read',
                                        choices=PERMISSIONS,
                                        verbose_name=_l('Permission Level'))

    class Meta:
        abstract = True
