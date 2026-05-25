from django.apps import AppConfig


class DjangoLedgerExtensionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_ledger_extensions'
    label = 'django_ledger_extensions'
    verbose_name = 'Django Ledger Extensions'

    def ready(self):
        import django_ledger_extensions.signals  # noqa: F401
