import graphene
from graphql_auth.schema import MeQuery, UserQuery


class QueryUser(UserQuery, MeQuery, graphene.ObjectType):
    pass
