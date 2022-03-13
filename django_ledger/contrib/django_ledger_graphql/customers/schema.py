import graphene
from graphene_django import DjangoObjectType

from django_ledger.models import CustomerModel, EntityModel


class CustomerList(DjangoObjectType):
    class Meta:
        model = CustomerModel


class EntityList(DjangoObjectType):
    class Meta:
        model = EntityModel


class CustomerQuery(graphene.ObjectType):
    all_customers = graphene.List(CustomerList, slug_name=graphene.String(required=True))

    def resolve_all_customers(self, info, slug_name):
        if info.context.user.is_authenticated:
            retuan = CustomerModel.objects.for_entity(
                entity_slug=slug_name,
                user_model=info.context.user
            ).order_by('-updated')
            return retuan
        else:
            return CustomerModel.objects.none()
