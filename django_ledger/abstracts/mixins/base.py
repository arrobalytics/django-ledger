from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _l

from django_ledger.io.roles import GROUP_INCOME, ASSET_CA_RECEIVABLES, ASSET_CA_CASH, LIABILITY_CL_ACC_PAYABLE


class SlugNameMixIn(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.slug


class CreateUpdateMixIn(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class ProgressibleMixIn(models.Model):
    progressible = models.BooleanField(default=False, verbose_name=_l('Progressible'))
    progress = models.DecimalField(null=True, blank=True, verbose_name=_l('Progress Amount'),
                                   decimal_places=2,
                                   max_digits=3,
                                   validators=[
                                       MinValueValidator(limit_value=0),
                                       MaxValueValidator(limit_value=1)
                                   ])

    class Meta:
        abstract = True


class LedgerBranchMixIn(ProgressibleMixIn):
    ledger = models.OneToOneField('django_ledger.LedgerModel',
                                  verbose_name=_l('Invoice Ledger'),
                                  on_delete=models.CASCADE)
    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_l('Invoice Cash Account'),
                                     related_name='invoices_cash',
                                     limit_choices_to={
                                         'role': ASSET_CA_CASH,
                                     })
    receivable_account = models.ForeignKey('django_ledger.AccountModel',
                                           on_delete=models.CASCADE,
                                           verbose_name=_l('Invoice Receivable Account'),
                                           related_name='invoices_ar',
                                           limit_choices_to={
                                               'role': ASSET_CA_RECEIVABLES
                                           })
    payable_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.CASCADE,
                                        verbose_name=_l('Invoice Liability Account'),
                                        related_name='invoices_ap',
                                        limit_choices_to={
                                            'role': LIABILITY_CL_ACC_PAYABLE
                                        })
    income_account = models.ForeignKey('django_ledger.AccountModel',
                                       on_delete=models.CASCADE,
                                       verbose_name=_l('Invoice Income Account'),
                                       related_name='invoices_in',
                                       limit_choices_to={
                                           'role__in': GROUP_INCOME
                                       })

    class Meta:
        abstract = True
