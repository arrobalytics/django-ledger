from django.apps import AppConfig


class DjangoLedgerExtensionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_ledger_extensions'
    label = 'django_ledger_extensions'
    verbose_name = 'Django Ledger Extensions'

    def ready(self):
        import django_ledger_extensions.signals  # noqa: F401

        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured

        from django_ledger_extensions.storage import beleg_storage_enabled

        if beleg_storage_enabled() and 'storages' not in settings.INSTALLED_APPS:
            raise ImproperlyConfigured(
                'DJANGO_LEDGER_AWS_STORAGE_BUCKET_NAME is set — add "storages" to INSTALLED_APPS.'
            )
