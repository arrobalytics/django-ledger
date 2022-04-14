import graphene

from graphene_django import DjangoObjectType

from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel


class CustomerType(DjangoObjectType):
    class Meta:
        model = CustomerModel


class CustomerMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation
        customer_name = graphene.String(required=True)
        address_1 = graphene.String(required=True)
        address_2 = graphene.String(required=True)
        city = graphene.String(required=True)
        state = graphene.String(required=True)
        zip_code = graphene.String(required=True)
        country = graphene.String(required=True)
        phone = graphene.String(required=True)
        email = graphene.String(required=True)
        website = graphene.String(required=True)
        slug_name = graphene.String(required=True)

    # The class attributes define the response of the mutation
    customer = graphene.Field(CustomerType)

    @classmethod
    def mutate(
            cls,
            root,
            info,
            customer_name,
            address_1,
            address_2,
            city,
            state,
            zip_code,
            country,
            phone,
            email,
            website,
            slug_name,
            **kwargs):
        customer_model = CustomerModel(
            customer_name=customer_name,
            address_1=address_1,
            address_2=address_2,
            city=city,
            state=state,
            zip_code=zip_code,
            country=country,
            phone=phone,
            email=email,
            website=website,
        )
        entity_model = EntityModel.objects.for_user(
            user_model=info.context.user
        ).get(slug__exact=slug_name)
        customer_model.entity = entity_model
        customer_model.save()
        # Notice we return an instance of this mutation
        return CustomerMutation(customer=customer_model)


class CustomerMutations(graphene.ObjectType):
    create_customer = CustomerMutation.Field()
