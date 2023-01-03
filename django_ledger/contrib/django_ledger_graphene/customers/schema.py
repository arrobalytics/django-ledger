import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from django_ledger.models import CustomerModel, EntityModel


class CustomerNode(DjangoObjectType):
    class Meta:
        model = CustomerModel
        filter_fields = {
            'customer_name': ['exact', 'icontains', 'istartswith'],
            'address_1': ['exact', 'icontains', 'istartswith'],
            'address_2': ['exact', 'icontains', 'istartswith'],
            'city': ['exact', 'icontains', 'istartswith'],
            'state': ['exact', 'icontains', 'istartswith'],
            'zip_code': ['exact', 'icontains', 'istartswith'],
            'country': ['exact', 'icontains', 'istartswith'],
            'phone': ['exact', 'icontains', 'istartswith'],
            'email': ['exact', 'icontains', 'istartswith'],
            'website': ['exact', 'icontains', 'istartswith'],
        }
        interfaces = (relay.Node,)
class EntityList(DjangoObjectType):
    class Meta:
        model = EntityModel

class CustomerQuery(graphene.ObjectType):
    all_customers = DjangoFilterConnectionField(CustomerNode, slug_name=graphene.String(required=True))

    def resolve_all_customers(self, info, slug_name, **kwargs):
        if info.context.user.is_authenticated:
            CustomerModel.objects.for_entity(
                entity_slug=slug_name,
                user_model=info.context.user
            ).order_by('-updated')
        else:
            return CustomerModel.objects.none()




