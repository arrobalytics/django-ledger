from django.conf import settings

USER_SETTINGS = getattr(settings, 'DJANGO_LEDGER_SETTINGS', dict())

DJANGO_LEDGER_SETTINGS = {
    'ACCOUNT_MAX_LENGTH': USER_SETTINGS.get('ACCOUNT_MAX_LENGTH', 10)
}