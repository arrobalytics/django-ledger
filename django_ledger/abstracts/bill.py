from random import choice
from string import ascii_uppercase, digits

from django.db import models
from django.utils.translation import gettext_lazy as _l

from django_ledger.abstracts.invoice import InvoiceModelManager
from django_ledger.abstracts.mixins.base import CreateUpdateMixIn, LedgerPlugInMixIn, ContactInfoMixIn

BILL_NUMBER_CHARS = ascii_uppercase + digits


def generate_bill_number(length=10):
    return 'B-' + ''.join(choice(BILL_NUMBER_CHARS) for _ in range(length))


class BillModelAbstract(LedgerPlugInMixIn,
                        ContactInfoMixIn,
                        CreateUpdateMixIn):
    REL_NAME_PREFIX = 'bill'
    IS_DEBIT_BALANCE = False
    ALLOW_MIGRATE = True

    bill_number = models.SlugField(max_length=20, unique=True, verbose_name=_l('Bill Number'))
    xref = models.SlugField(null=True, blank=True, verbose_name=_l('External Reference Number'))

    cash_account = models.ForeignKey('django_ledger.AccountModel',
                                     on_delete=models.CASCADE,
                                     verbose_name=_l('Cash Account'),
                                     related_name=f'{REL_NAME_PREFIX}_cash_account')
    receivable_account = models.ForeignKey('django_ledger.AccountModel',
                                           on_delete=models.CASCADE,
                                           verbose_name=_l('Receivable Account'),
                                           related_name=f'{REL_NAME_PREFIX}_receivable_account')
    payable_account = models.ForeignKey('django_ledger.AccountModel',
                                        on_delete=models.CASCADE,
                                        verbose_name=_l('Payable Account'),
                                        related_name=f'{REL_NAME_PREFIX}_payable_account')
    earnings_account = models.ForeignKey('django_ledger.AccountModel',
                                         on_delete=models.CASCADE,
                                         verbose_name=_l('Earnings Account'),
                                         related_name=f'{REL_NAME_PREFIX}_earnings_account')

    objects = InvoiceModelManager()

    class Meta:
        abstract = True
        ordering = ['-updated']
        verbose_name = _l('Bill')
        verbose_name_plural = _l('Bills')

    def __str__(self):
        return f'Bill: {self.bill_number}'

    def get_migrate_state_desc(self):
        """
        Must be implemented.
        :return:
        """
        return f'Bill {self.bill_number} account adjustment.'

    def clean(self):
        if not self.bill_number:
            self.bill_number = generate_bill_number()

        # todo: this is not executing the mixin clean() method...
        super().clean()
