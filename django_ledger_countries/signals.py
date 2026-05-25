"""
Country-level signal wiring.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from django_ledger.models.entity import EntityModel
from django_ledger.regional.dispatch import dispatch_on_entity_created


@receiver(post_save, sender=EntityModel)
def entity_created_regional_hook(sender, instance, created, **kwargs):
    if created:
        dispatch_on_entity_created(instance)
