from django.conf import settings

from django_ledger import __version__
from django_ledger.settings import DJANGO_LEDGER_THEME


def django_ledger_context(request):
    return {
        'DEBUG': settings.DEBUG,
        'VERSION': __version__,
        'DJANGO_LEDGER_THEME': DJANGO_LEDGER_THEME,
    }
