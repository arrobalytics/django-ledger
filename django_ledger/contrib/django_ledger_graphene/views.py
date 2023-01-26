from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from oauth2_provider.views import ProtectedResourceView


@method_decorator(csrf_exempt, name='dispatch')
class ProtectedOAuth2GraphQLView(
    ProtectedResourceView,
    GraphQLView
):
    raise_exception = True
