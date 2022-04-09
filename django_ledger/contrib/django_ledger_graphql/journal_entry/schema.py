import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django_ledger.models import JournalEntryModel
from graphene_django.filter import DjangoFilterConnectionField


class JournalEntryNode(DjangoObjectType):
    class Meta:
        model = JournalEntryModel
        filter_fields = {
            'parent': ['exact'],
            'activity': ['exact', 'icontains', 'istartswith'],
            'date': ['exact'],
            'description': ['exact'],
        }
        interfaces = (relay.Node,)


class JournalEntryQuery(graphene.ObjectType):
    all_journal_entries = DjangoFilterConnectionField(
        JournalEntryNode, slug_name=graphene.String(
            required=True), pk_ledger=graphene.UUID())

    def resolve_all_journal_entry(self, info, slug_name, pk_ledger, **kwargs):
        if info.context.user.is_authenticated:
            sort = info.context.GET.get('sort')
            if not sort:
                sort = '-updated'
                return JournalEntryModel.on_coa.for_ledger(
                    ledger_pk=pk_ledger,
                    entity_slug=slug_name,
                    user_model=info.context.user
                ).order_by(sort)
        else:
            return JournalEntryModel.objects.none()
