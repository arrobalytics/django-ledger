"""
Optional S3-backed storage for supporting documents.

Configure in project settings::

    STORAGES = {
        'default': {...},
        'supporting_documents': {
            'BACKEND': 'django_ledger_extensions.storage.get_supporting_document_storage',
        },
    }

Or keep the default local ``FileSystemStorage``.
"""
from __future__ import annotations

from django.conf import settings
from django.core.files.storage import FileSystemStorage, default_storage
from django.utils.module_loading import import_string


def get_supporting_document_storage():
    backend = getattr(
        settings,
        'DJANGO_LEDGER_SUPPORTING_DOCUMENT_STORAGE',
        None,
    )
    if backend:
        return import_string(backend)()
    return default_storage if default_storage else FileSystemStorage()
