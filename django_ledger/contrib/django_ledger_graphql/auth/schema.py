import graphene

from graphql_auth.schema import UserQuery, MeQuery

class AuthQuery(UserQuery, MeQuery, graphene.ObjectType):
    pass
