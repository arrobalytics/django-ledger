import graphene

from graphql_auth.schema import UserQuery, MeQuery

class QueryUser(UserQuery, MeQuery, graphene.ObjectType):
    pass