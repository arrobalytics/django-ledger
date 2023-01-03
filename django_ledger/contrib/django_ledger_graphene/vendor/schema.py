import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from django_ledger.models import VendorModel


class VendorNode(DjangoObjectType):
    class Meta:
        model = VendorModel
        filter_fields = {
            'vendor_name': ['exact', 'icontains', 'istartswith'],
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


class VendorsQuery(graphene.ObjectType):
    all_vendors = DjangoFilterConnectionField(VendorNode, slug_name=graphene.String(required=True))

    def resolve_all_vendors(self, info, slug_name, **kwargs):
        if info.context.user.is_authenticated:
            return VendorModel.objects.for_entity(
                entity_slug=slug_name,
                user_model=info.context.user
            ).order_by('-updated')
        else:
            return VendorModel.objects.none()
