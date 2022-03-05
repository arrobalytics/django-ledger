from django.urls import reverse
import graphene
from django.utils.functional import SimpleLazyObject

from .customers.schema import CustomerQuery

API_PATH = SimpleLazyObject(lambda: reverse("api"))


class Query(
    CustomerQuery,
):
    pass

schema = graphene.Schema(query=Query)
