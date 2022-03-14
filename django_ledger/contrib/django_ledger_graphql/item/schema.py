
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
