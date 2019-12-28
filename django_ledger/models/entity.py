from random import randint

from django.db.models.signals import pre_save, post_save
from django.utils.text import slugify

from django_ledger.models.coa import ChartOfAccountModel
from django_ledger.models_abstracts.entity import EntityModelAbstract, EntityManagementModelAbstract


class EntityModel(EntityModelAbstract):
    """
    Entity Model Base Class From Abstract
    """


def entity_presave(sender, instance, **kwargs):
    if not instance.slug:
        slug = slugify(instance.name)
        ri = randint(100000, 999999)
        entity_slug = f'{slug}-{ri}'
        instance.slug = entity_slug


pre_save.connect(entity_presave, EntityModel)


def entity_postsave(sender, instance, **kwargs):
    if not getattr(instance, 'coa', None):
        ChartOfAccountModel.objects.create(
            slug=instance.slug + '-coa',
            name=instance.name + ' CoA',
            entity=instance
        )


post_save.connect(entity_postsave, EntityModel)


class EntityManagementModel(EntityManagementModelAbstract):
    """
    EntityManagement Model Base Class From Abstract
    """
