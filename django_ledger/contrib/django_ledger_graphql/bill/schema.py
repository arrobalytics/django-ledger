import graphene
from graphene_django import DjangoObjectType

from django_ledger.models import BillModel


class BillList(DjangoObjectType):
    class Meta:
        model = BillModel


class Bill_list_Query(graphene.ObjectType):
    all_bills = graphene.List(BillList, slug_name=graphene.String(required=True))

    def resolve_all_bills(self, info, slug_name):
        if info.context.user.is_authenticated:
            return BillModel.objects.for_entity(
                entity_slug=slug_name,
                user_model=info.context.user
            ).select_related('vendor').order_by('-updated')
        else:
            return BillModel.objects.none()
