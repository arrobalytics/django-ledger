from django.urls import reverse
import graphene
from django.utils.functional import SimpleLazyObject

from .customers.schema import CustomerQuery
from django_ledger.contrib.django_ledger_graphql.bill.schema import Bill_list_Query

API_PATH = SimpleLazyObject(lambda: reverse("api"))


class Query(
    CustomerQuery,
    Bill_list_Query,
):
    pass


schema = graphene.Schema(query=Query)
