from django_ledger.settings import DJANGO_LEDGER_SETTINGS
from model_base import load_model_abstract

TransactionModelAbstract = load_model_abstract(DJANGO_LEDGER_SETTINGS.get('TRANSACTION_MODEL_ABSTRACT'))


class TransactionModel(TransactionModelAbstract):
    pass
# class TransactionModel(CreateUpdateMixIn):
#     TX_TYPE = [
#         ('credit', _('Credit')),
#         ('debit', _('Debit'))
#     ]
#     tx_type = models.CharField(max_length=10, choices=TX_TYPE, verbose_name=_l('Tx Type'))
#     journal_entry = models.ForeignKey('django_ledger.JournalEntryModel',
#                                       related_name='txs',
#                                       verbose_name=_l('Journal Entry'),
#                                       on_delete=models.CASCADE)
#     account = models.ForeignKey('django_ledger.AccountModel',
#                                 related_name='txs',
#                                 verbose_name=_l('Account'),
#                                 on_delete=models.PROTECT)
#     amount = models.DecimalField(decimal_places=2,
#                                  max_digits=20,
#                                  null=True,
#                                  blank=True,
#                                  verbose_name=_l('Amount'),
#                                  validators=[MinValueValidator(0)])
#
#     description = models.CharField(max_length=100, null=True, blank=True, verbose_name=_l('Tx Description'))
#
#     class Meta:
#         verbose_name = _l('Transaction')
#         verbose_name_plural = _l('Transactions')
#
#     def __str__(self):
#         return '{x1}-{x2}/{x5}: {x3}/{x4}'.format(x1=self.account.code,
#                                                   x2=self.account.name,
#                                                   x3=self.amount,
#                                                   x4=self.tx_type,
#                                                   x5=self.account.balance_type)
