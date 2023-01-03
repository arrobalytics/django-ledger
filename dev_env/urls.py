from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

from django_ledger.settings import DJANGO_LEDGER_GRAPHQL_ENABLED

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('django_ledger.urls', namespace='django_ledger')),
]

try:
    if DJANGO_LEDGER_GRAPHQL_ENABLED:
        # checking for graphene_django installation to provide and enable graphql services...
        from graphene_django.views import GraphQLView
        from django_ledger.contrib.django_ledger_graphene.api import schema

        urlpatterns += [
            path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=True, schema=schema)))
        ]

except ImportError:
    pass
