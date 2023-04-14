from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from django_ledger.settings import DJANGO_LEDGER_GRAPHQL_ENABLED

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('django_ledger.urls', namespace='django_ledger')),
]

# GraphQl API Support...
try:
    if DJANGO_LEDGER_GRAPHQL_ENABLED:
        from django_ledger.contrib.django_ledger_graphene.api import schema
        from django_ledger.contrib.django_ledger_graphene.views import DjangoLedgerOAuth2GraphQLView

        urlpatterns += [
            path('api/v1/graphql/', DjangoLedgerOAuth2GraphQLView.as_view(graphiql=settings.DEBUG, schema=schema)),
            path('api/v1/o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
        ]

except ImportError:
    pass
