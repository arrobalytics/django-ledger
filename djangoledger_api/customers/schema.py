import graphene
from graphene_django import DjangoObjectType
from django_ledger.models.customer import CustomerModel


class CustomerList(DjangoObjectType):
    """testing API
    """
    class Meta:
        model = CustomerModel
        fields = ("city",)


class CustomerQuery(graphene.ObjectType):
    all_customers = graphene.List(CustomerList)

    def resolve_all_customers(root, info):
        return CustomerModel.objects.all()

