from django.db.models.signals import pre_save, post_save
from django.utils.translation import gettext as _

from django_ledger.models.coa import ChartOfAccountModel
from django_ledger.models_abstracts.entity import EntityModelAbstract, EntityManagementModelAbstract


class EntityModel(EntityModelAbstract):
    """
    Entity Model Base Class From Abstract
    """


def entity_presave(sender, instance, **kwargs):
    instance.clean()


pre_save.connect(entity_presave, EntityModel)


def entity_postsave(sender, instance, **kwargs):
    if not getattr(instance, 'coa', None):
        ChartOfAccountModel.objects.create(
            slug=instance.slug + '-coa',
            name=instance.name + ' CoA',
            entity=instance
        )
    if getattr(instance, 'CREATE_GL_FLAG', False):
        instance.ledgers.create(
            name=_('General Ledger')
        )
        instance.CREATE_GL_FLAG = False


post_save.connect(entity_postsave, EntityModel)


class EntityManagementModel(EntityManagementModelAbstract):
    """
    EntityManagement Model Base Class From Abstract
    """
