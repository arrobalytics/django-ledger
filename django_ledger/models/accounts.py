from django.db.models.signals import pre_save

from django_ledger.abstracts.accounts import AccountModelAbstract


class AccountModel(AccountModelAbstract):
    """
    Base Account Model from Account Model Abstract Class
    """


def accountmodel_presave(sender, instance, *args, **kwargs):
    print('Account {x1}-{x2} Saved'.format(x1=instance.code,
                                           x2=instance.name))


pre_save.connect(accountmodel_presave, sender=AccountModel)
