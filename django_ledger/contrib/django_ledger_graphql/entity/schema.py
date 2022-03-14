
import graphene
from graphene_django import DjangoObjectType
from django_ledger.models import EntityModel


class EntitytList(DjangoObjectType):
    class Meta:
        model = EntityModel


class Entity_Query(graphene.ObjectType):
    all_entity_list = graphene.List(EntitytList)

    def resolve_all_entity_list(self, info):
        if info.context.user.is_authenticated:
            return EntityModel.objects.for_user(
                user_model=info.context.user)
        else:
            return EntityModel.objects.none()
