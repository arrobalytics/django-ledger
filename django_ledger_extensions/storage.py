"""
Beleg (supporting document) file storage — local disk or S3.

Enable S3 by setting one Django setting::

    INSTALLED_APPS += ['storages']
    DJANGO_LEDGER_AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'

AWS credentials use the normal boto3 chain (env vars, ``~/.aws/credentials``,
or IAM role on EC2/ECS/Lambda). Optional overrides:

- ``DJANGO_LEDGER_AWS_S3_REGION_NAME`` (default ``eu-central-1``)
- ``DJANGO_LEDGER_AWS_STORAGE_LOCATION`` (default ``belege`` — key prefix in bucket)
"""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage, default_storage

_storage_cache: dict[str, object] = {}


def _bucket_name() -> str:
    return getattr(settings, 'DJANGO_LEDGER_AWS_STORAGE_BUCKET_NAME', '') or ''


def beleg_storage_enabled() -> bool:
    return bool(_bucket_name())


def _build_storage(cache_key: str):
    if cache_key == '__local__':
        return default_storage if default_storage else FileSystemStorage()

    try:
        from storages.backends.s3boto3 import S3Boto3Storage
    except ImportError as exc:
        raise ImproperlyConfigured(
            'DJANGO_LEDGER_AWS_STORAGE_BUCKET_NAME is set but django-storages is not '
            'installed. Run: pip install "django-ledger[s3]" or pip install django-storages boto3'
        ) from exc

    region = getattr(settings, 'DJANGO_LEDGER_AWS_S3_REGION_NAME', 'eu-central-1')
    location = getattr(settings, 'DJANGO_LEDGER_AWS_STORAGE_LOCATION', 'belege')

    return S3Boto3Storage(
        bucket_name=cache_key,
        region_name=region,
        location=location,
        default_acl='private',
        file_overwrite=False,
        querystring_auth=True,
    )


def get_beleg_storage():
    cache_key = _bucket_name() or '__local__'
    if cache_key not in _storage_cache:
        _storage_cache[cache_key] = _build_storage(cache_key)
    return _storage_cache[cache_key]


def clear_beleg_storage_cache() -> None:
    _storage_cache.clear()


# Backwards-compatible alias used in older docs.
get_supporting_document_storage = get_beleg_storage
