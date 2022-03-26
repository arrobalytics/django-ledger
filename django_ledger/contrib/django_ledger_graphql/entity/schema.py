
import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django_ledger.models import EntityModel
from graphene_django.filter import DjangoFilterConnectionField


class EntityNode(DjangoObjectType):
    class Meta:
        model = EntityModel
        filter_fields = {
            'name': ['exact', 'icontains', 'istartswith'],
        }
        interfaces = (relay.Node,)


class Entity_Query(graphene.ObjectType):
    all_entity_list = DjangoFilterConnectionField(EntityNode)

class EntitytList(DjangoObjectType):
    class Meta:
        model = EntityModel


class Entity_Query(graphene.ObjectType):
    all_entity_list = graphene.List(EntitytList)
    def resolve_all_entity_list(self, info, **kwargs):

        if info.context.user.is_authenticated:
            return EntityModel.objects.for_user(
                user_model=info.context.user)
        else:
            return EntityModel.objects.none()