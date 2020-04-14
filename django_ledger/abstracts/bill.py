from datetime import datetime, timedelta
from decimal import Decimal
from random import choice
from string import ascii_uppercase, digits

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _l

from django_ledger.abstracts.invoice import InvoiceModelManager
from django_ledger.abstracts.mixins.base import CreateUpdateMixIn, LedgerPlugInMixIn, NameAddressMixIn
from django_ledger.io.roles import GROUP_INCOME, ASSET_CA_CASH, LIABILITY_CL_ACC_PAYABLE, ASSET_CA_RECEIVABLES

BILL_NUMBER_CHARS = ascii_uppercase + digits


def generate_bill_number(length=10):
    return 'B-' + ''.join(choice(BILL_NUMBER_CHARS) for _ in range(length))


class BillModelAbstract(LedgerPlugInMixIn,
                        NameAddressMixIn,
                        CreateUpdateMixIn):
    BALANCE_TYPE = 'credit'
    REL_NAME_PREFIX = 'bill'
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
    income_account = models.ForeignKey('django_ledger.AccountModel',
                                       on_delete=models.CASCADE,
                                       verbose_name=_l('Income Account'),
                                       related_name=f'{REL_NAME_PREFIX}_income_account')

    objects = InvoiceModelManager()

    class Meta:
        abstract = True

    def clean(self):
        if not self.bill_number:
            self.bill_number = generate_bill_number()

        if not self.date:
            self.date = datetime.now().date()
        if self.cash_account.role != ASSET_CA_CASH:
            raise ValidationError(f'Cash account must be of role {ASSET_CA_CASH}')
        if self.receivable_account.role != ASSET_CA_RECEIVABLES:
            raise ValidationError(f'Receivable account must be of role {ASSET_CA_RECEIVABLES}')
        if self.payable_account.role != LIABILITY_CL_ACC_PAYABLE:
            raise ValidationError(f'Payable account must be of role {LIABILITY_CL_ACC_PAYABLE}')
        if self.income_account.role not in GROUP_INCOME:
            raise ValidationError(f'Income account must be of role {GROUP_INCOME}')
        if self.progressible and self.progress is None:
            self.progress = 0

        if self.terms != 'on_receipt':
            self.due_date = self.date + timedelta(days=int(self.terms.split('_')[-1]))
        else:
            self.due_date = self.date

        if self.paid:
            self.progress = Decimal(1.0)
            self.amount_paid = self.amount_due

            today = datetime.now().date()
            if not self.paid_date:
                self.paid_date = today
            if self.paid_date > today:
                raise ValidationError('Cannot pay invoice in the future.')
            if self.paid_date < self.date:
                raise ValidationError('Cannot pay invoice before invoice date.')
        else:
            self.paid_date = None
