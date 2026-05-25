from django.apps import AppConfig


class DjangoLedgerCountriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_ledger_countries'
    label = 'django_ledger_countries'
    verbose_name = 'Django Ledger Countries'

    def ready(self):
        import django_ledger_countries.signals  # noqa: F401
        from django_ledger_countries.registry import get_active_plugin

        get_active_plugin().register_roles()
