"""
Signal handlers bridging core django-ledger events to regional plugins.
"""
from django.dispatch import receiver

from django_ledger.models.signals import journal_entry_posted
from django_ledger.regional.dispatch import (
    dispatch_on_journal_entry_posted,
    dispatch_validate_journal_entry,
)


@receiver(journal_entry_posted)
def regional_journal_entry_posted(sender, instance, commited=False, **kwargs):
    if commited:
        dispatch_validate_journal_entry(instance)
    dispatch_on_journal_entry_posted(instance, committed=commited)


@receiver(journal_entry_posted)
def lock_supporting_documents_on_post(sender, instance, commited=False, **kwargs):
    if not commited:
        return

    from django.contrib.contenttypes.models import ContentType
    from django_ledger_extensions.models import SupportingDocumentModel

    ct = ContentType.objects.get_for_model(instance)
    SupportingDocumentModel.objects.filter(
        content_type=ct,
        object_id=instance.uuid,
        immutable=False,
    ).update(immutable=True)
