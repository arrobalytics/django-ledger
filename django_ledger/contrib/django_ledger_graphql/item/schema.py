import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django_ledger.models import UnitOfMeasureModel
from graphene_django.filter import DjangoFilterConnectionField

class UnitOfMeasureNode(DjangoObjectType):
    class Meta:
        model = UnitOfMeasureModel
        filter_fields = {
            'name' : ['exact', 'icontains', 'istartswith'],
            'unit_abbr': ['exact', 'icontains', 'istartswith'],
            'is_active' : ['exact']
        }
        interfaces = (relay.Node,)


class UnitOfMeasureQuery(graphene.ObjectType):
    all_unit_of_measure = DjangoFilterConnectionField(UnitOfMeasureNode, slug_name=graphene.String(required=True))

import graphene
from graphene_django import DjangoObjectType
from django_ledger.models import UnitOfMeasureModel


class UnitOfMeasureList(DjangoObjectType):
    class Meta:
        model = UnitOfMeasureModel


class UnitOfMeasureQuery(graphene.ObjectType):
    all_unit_of_measure = graphene.List(
        UnitOfMeasureList,
        slug_name=graphene.String(
            required=True))

    def resolve_all_unit_of_measure(self, info, slug_name):
        if info.context.user.is_authenticated:
            return UnitOfMeasureModel.objects.for_entity(
                entity_slug=slug_name,
                user_model=info.context.user
            )
        else:
            return UnitOfMeasureModel.objects.none()
