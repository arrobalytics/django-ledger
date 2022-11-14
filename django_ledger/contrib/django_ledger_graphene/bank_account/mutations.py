import graphene

from graphene_django import DjangoObjectType

from django_ledger.models.bank_account import BankAccountModel


class BankAccountType(DjangoObjectType):
    class Meta:
        model = BankAccountModel
        convert_choices_to_enum = True



class BankAccountMutation(graphene.Mutation):
    class Arguments:
        # The input arguments for this mutation

        name = graphene.String(required=True)
        account_type = graphene.String(required=True)
        account_number = graphene.String(required=True)
        routing_number = graphene.String(required=True)
        aba_number = graphene.String(required=True)
        cash_account = graphene.ID(required=True)
        active = graphene.Boolean(required=True)
        slug_name = graphene.String(required=True)
    # The class attributes define the response of the mutation
    bank_account = graphene.Field(BankAccountType)

    @classmethod
    def mutate(
            cls,
            root,
            info,
            name,
            account_type,
            account_number,
            routing_number,
            aba_number,
            cash_account,
            active,
            slug_name,
            **kwargs):
        bank_account_model=BankAccountModel(
            name=name,
            account_type=account_type,
            account_number=account_number,
            routing_number=routing_number,
            aba_number=aba_number,
            cash_account=cash_account,
            active=active,
        )
        bank_account_model, entity_model = bank_account_model.configure(
            entity_slug=slug_name,
            user_model=info.context.user)
        bank_account_model.save()
        # Notice we return an instance of this mutation
        return BankAccountMutation(bank_account=bank_account_model)


class BankAccountMutations(graphene.ObjectType):
    create_bank_account = BankAccountMutation.Field()
