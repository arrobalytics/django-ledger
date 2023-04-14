import graphene
from graphene import relay
from graphene_django import DjangoObjectType

from django_ledger.models import EntityModel, EntityModelQuerySet

ENTITY_MODEL_BASE_FIELDS = [
    'uuid',
    'slug',
    'name',
    'accrual_method',
    'fy_start_month',
    'picture',
    'is_admin',
    'hidden',
    'created',
    'updated'
]


class EntityModelType(DjangoObjectType):
    is_admin = graphene.Boolean()

    def resolve_is_admin(self, info):
        entity_model: EntityModel = self
        return entity_model.is_admin_user(user_model=info.context.resource_owner)

    class Meta:
        model = EntityModel
        fields = ENTITY_MODEL_BASE_FIELDS
        filter_fields = {
            'name': [
                'exact',
                'icontains',
                'istartswith'
            ],
        }
        interfaces = (relay.Node,)


class EntityModelTypeDetail(EntityModelType):
    class Meta:
        model = EntityModel
        fields = ENTITY_MODEL_BASE_FIELDS + [
            'default_coa'
        ]


class EntityModelQuery(graphene.ObjectType):
    entity_model_list_all = graphene.List(EntityModelType)
    entity_model_list_visible = graphene.List(EntityModelType)
    entity_model_list_hidden = graphene.List(EntityModelType)
    entity_model_list_managed = graphene.List(EntityModelType)
    entity_model_list_is_admin = graphene.List(EntityModelType)

    entity_model_detail_by_uuid = graphene.Field(EntityModelTypeDetail, uuid=graphene.String(required=True))
    entity_model_detail_by_slug = graphene.Field(EntityModelTypeDetail, slug=graphene.String(required=True))

    @staticmethod
    def get_base_queryset(info):
        if info.context.resource_owner.is_authenticated:
            return EntityModel.objects.for_user(user_model=info.context.resource_owner)
        return EntityModel.objects.none()

    # list ....
    def resolve_entity_model_list_all(self, info, **kwargs):
        return EntityModelQuery.get_base_queryset(info)

    def resolve_entity_model_list_visible(self, info, **kwargs):
        qs = EntityModelQuery.get_base_queryset(info)
        return qs.visible()

    def resolve_entity_model_list_hidden(self, info, **kwargs):
        qs = EntityModelQuery.get_base_queryset(info)
        return qs.hidden()

    def resolve_entity_model_list_managed(self, info, **kwargs):
        qs: EntityModelQuerySet = EntityModelQuery.get_base_queryset(info)
        user_model = info.context.resource_owner
        return qs.filter(managers__in=[user_model])

    def resolve_entity_model_list_is_admin(self, info, **kwargs):
        qs: EntityModelQuerySet = EntityModelQuery.get_base_queryset(info)
        user_model = info.context.resource_owner
        return qs.filter(admin=user_model)

    # detail...
    def resolve_entity_model_detail_by_slug(self, info, slug, **kwargs):
        qs: EntityModelQuerySet = EntityModelQuery.get_base_queryset(info)
        return qs.select_related('default_coa').get(slug__exact=slug)

    def resolve_entity_model_detail_by_uuid(self, info, uuid, **kwargs):
        qs: EntityModelQuerySet = EntityModelQuery.get_base_queryset(info)
        return qs.select_related('default_coa').get(uuid__exact=uuid)
