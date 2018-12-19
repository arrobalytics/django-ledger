from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.db.models.signals import pre_save, post_init
from mptt.models import MPTTModel, TreeForeignKey

from .mixins import CreateUpdateMixIn

# todo: Move to a settings module.
LEDGER_ACCOUNTMAXLENGTH = 5

class AccountModelAbstract(MPTTModel,
                           CreateUpdateMixIn):
    ACCOUNT_ROLE = [
        ('Assets', (
            ('ca', 'Current Asset'),
            ('lti', 'Long Term Investments'),
            ('ppe', 'Property Plant & Equipment'),
            ('ia', 'Intangible Assets'),
            ('aadj', 'Asset Adjustments'),
        )
         ),
        ('Liabilities', (
            ('cl', 'Current Liabilities'),
            ('ltl', 'Long Term Liabilities'),
        )
         ),
        ("Equity", (
            ('cap', 'Capital'),
            ('cadj', 'Capital Adjustments'),
            ('in', 'Income'),
            ('ex', 'Expense'),
        )
         ),
        ("Other", (
            ('excl', 'Excluded'),
        )
         )
    ]

    BALANCE_TYPE = [
        ('credit', 'Credit'),
        ('debit', 'Debit')
    ]

    code = models.CharField(max_length=LEDGER_ACCOUNTMAXLENGTH, unique=True, verbose_name='Account Code')
    name = models.CharField(max_length=100, verbose_name='Account Name')
    parent = TreeForeignKey('self',
                            null=True,
                            blank=True,
                            related_name='children',
                            db_index=True,
                            on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ACCOUNT_ROLE, verbose_name='Account Role')
    role_bs = models.CharField(max_length=20, null=True, verbose_name='Balance Sheet Role')
    balance_type = models.CharField(max_length=6, choices=BALANCE_TYPE, verbose_name='Account Balance Type')
    locked = models.BooleanField(default=False)

    class Meta:
        abstract = True

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        return '{x1} - {x5}: {x2} ({x3}/{x4})'.format(x1=self.role_bs.upper(),
                                                      x2=self.name,
                                                      x3=self.role.upper(),
                                                      x4=self.balance_type,
                                                      x5=self.code)

    def get_bs_role(self):
        if self.role:
            for role, value in dict(self.ACCOUNT_ROLE).items():
                if self.role in [x[0] for x in value]:
                    return role.lower()

    def set_bs_role(self):
        """
        Account Balance Sheet Role is automatically checked during save and Model's clean() operation.

        """
        if not self.role_bs:
            self.role_bs = self.get_bs_role()

    def check_bs_role(self):
        return self.role_bs == self.get_bs_role()

    def clean(self):

        if not self.check_bs_role():
            self.set_bs_role()

    def get_balance(self):

        credits = self.txs.filter(
            tx_type__exact='credit').aggregate(
            credits=Coalesce(Sum('amount'), 0))['credits']

        debits = self.txs.filter(
            tx_type__exact='debit').aggregate(
            debits=Coalesce(Sum('amount'), 0))['debits']

        if self.balance_type == 'credit':
            return credits - debits
        elif self.balance_type == 'debit':
            return debits - credits


class AccountModel(AccountModelAbstract):
    """
    Final AccountModel from Abstracts
    """


# AccountModel Signals ----------------
# def accountmodel_postinit(sender, instance, *args, **kwargs):
#     print('Hello Account {x1}-{x2} Post Init'.format(x1=instance.code,
#                                                      x2=instance.name))
#
#
# post_init.connect(accountmodel_postinit, sender=AccountModel)


def accountmodel_presave(sender, instance, raw, using, update_fields, *args, **kwargs):
    print('Hello Account {x1}-{x2} Pre Save'.format(x1=instance.code,
                                                    x2=instance.name))
    if not instance.check_bs_role():
        instance.set_bs_role()


pre_save.connect(accountmodel_presave, sender=AccountModel)
