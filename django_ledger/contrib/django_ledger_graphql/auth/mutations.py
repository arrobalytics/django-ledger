from django.contrib.auth import get_user_model
import graphene
from graphene_django import DjangoObjectType
import graphql_jwt
from graphql_auth import mutations
## register new user without graphql_auth ##

# class UserType(DjangoObjectType):
#    class Meta:
#       model = get_user_model()
# 
# class CreateUser(graphene.Mutation):
#    user = graphene.Field(UserType)
#    class Arguments:
#       username = graphene.String(required=True)
#       password = graphene.String(required=True)
#       email = graphene.String(required=True)
# 
#    def mutate(self, info, username, password, email):
#       user = get_user_model()(
#          username=username,
#          email=email,
#       )
#       user.set_password(password)
#       user.save()
#       return CreateUser(user=user)
# 
# class CreateUserMutation(graphene.ObjectType):
#    create_user = CreateUser.Field()

class AuthMutation(graphene.ObjectType):
    register = mutations.Register.Field()
    verify_account = mutations.VerifyAccount.Field()
    resend_activation_email = mutations.ResendActivationEmail.Field()
    send_password_reset_email = mutations.SendPasswordResetEmail.Field()
    password_reset = mutations.PasswordReset.Field()
    password_change = mutations.PasswordChange.Field()
    archive_account = mutations.ArchiveAccount.Field()
    delete_account = mutations.DeleteAccount.Field()
    update_account = mutations.UpdateAccount.Field()
    send_secondary_email_activation = mutations.SendSecondaryEmailActivation.Field()
    verify_secondary_email = mutations.VerifySecondaryEmail.Field()
    swap_emails = mutations.SwapEmails.Field()

    # django-graphql-jwt inheritances
    token_auth = mutations.ObtainJSONWebToken.Field()
    verify_token = mutations.VerifyToken.Field()
    refresh_token = mutations.RefreshToken.Field()
    revoke_token = mutations.RevokeToken.Field()