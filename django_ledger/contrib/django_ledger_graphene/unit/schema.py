import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from django_ledger.models import EntityUnitModel


class EntityUnitNode(DjangoObjectType):
    class Meta:
        model = EntityUnitModel
        filter_fields = {
            'name': ['exact', 'icontains', 'istartswith'],
        }
        interfaces = (relay.Node,)
class EntityUnitQuery(graphene.ObjectType):
    all_entity_unit = DjangoFilterConnectionField(EntityUnitNode, slug_name=graphene.String(required=True))

    def resolve_all_vendors(self, info, slug_name, **kwargs):
        if info.context.user.is_authenticated:
            return EntityUnitModel.objects.for_entity(
            entity_slug=slug_name,
            user_model=info.context.user
        )
        else:
            return EntityUnitModel.objects.none()

