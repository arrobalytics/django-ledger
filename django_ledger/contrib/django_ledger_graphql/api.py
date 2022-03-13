import graphene
from django.urls import reverse
from django.utils.functional import SimpleLazyObject

from django_ledger.contrib.django_ledger_graphql.accounts.schema import Accountlist_Query
from django_ledger.contrib.django_ledger_graphql.bank_account.schema import Bank_account_Query
from django_ledger.contrib.django_ledger_graphql.bill.schema import Bill_list_Query
from django_ledger.contrib.django_ledger_graphql.customers.schema import CustomerQuery

API_PATH = SimpleLazyObject(lambda: reverse("api"))


class Query(
    CustomerQuery,
    Bill_list_Query,
    Accountlist_Query,
    Bank_account_Query,
):
    pass


schema = graphene.Schema(query=Query)
