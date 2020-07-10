# from random import choice
# from string import ascii_uppercase, digits
#
# from django.db import models
# from django.db.models import Q
# from django.urls import reverse
# from django.utils.translation import gettext_lazy as _
#
# from django_ledger.abstracts.mixins.base import CreateUpdateMixIn, ProgressibleMixIn, ContactInfoMixIn
# from django_ledger.models.entity import EntityModel
#
#
# class LazyLoader:
#     TXS_MODEL = None
#
#     def get_txs_model(self):
#         if not self.TXS_MODEL:
#             from django_ledger.models.transactions import TransactionModel
#             self.TXS_MODEL = TransactionModel
#         return self.TXS_MODEL
#
#
# lazy_loader = LazyLoader()
#
# INVOICE_NUMBER_CHARS = ascii_uppercase + digits
#
#
# def generate_invoice_number(length=10):
#     return 'I-' + ''.join(choice(INVOICE_NUMBER_CHARS) for _ in range(length))
#
#
# class InvoiceModelManager(models.Manager):
#
#     def for_user(self, user_model):
#         return self.get_queryset().filter(
#             Q(ledger__entity__admin=user_model) |
#             Q(ledger__entity__managers__in=[user_model])
#         )
#
#     def on_entity(self, entity):
#         if isinstance(entity, EntityModel):
#             return self.get_queryset().filter(ledger__entity=entity)
#         elif isinstance(entity, str):
#             return self.get_queryset().filter(ledger__entity__slug__exact=entity)
#
#
# class InvoiceModelAbstract(ProgressibleMixIn,
#                            ContactInfoMixIn,
#                            CreateUpdateMixIn):
#     IS_DEBIT_BALANCE = True
#     REL_NAME_PREFIX = 'invoice'
#
#     # todo: can add help text here....?
#     invoice_to = models.CharField(max_length=100, verbose_name=_('Invoice To'))
#     invoice_number = models.SlugField(max_length=20, unique=True, verbose_name=_('Invoice Number'))
#
#     cash_account = models.ForeignKey('django_ledger.AccountModel',
#                                      on_delete=models.CASCADE,
#                                      verbose_name=_('Cash Account'),
#                                      related_name=f'{REL_NAME_PREFIX}_cash_account')
#     receivable_account = models.ForeignKey('django_ledger.AccountModel',
#                                            on_delete=models.CASCADE,
#                                            verbose_name=_('Receivable Account'),
#                                            related_name=f'{REL_NAME_PREFIX}_receivable_account')
#     payable_account = models.ForeignKey('django_ledger.AccountModel',
#                                         on_delete=models.CASCADE,
#                                         verbose_name=_('Payable Account'),
#                                         related_name=f'{REL_NAME_PREFIX}_payable_account')
#     earnings_account = models.ForeignKey('django_ledger.AccountModel',
#                                          on_delete=models.CASCADE,
#                                          verbose_name=_('Earnings Account'),
#                                          related_name=f'{REL_NAME_PREFIX}_earnings_account')
#
#     objects = InvoiceModelManager()
#
#     class Meta:
#         abstract = True
#         ordering = ['-updated']
#         verbose_name = _('Invoice')
#         verbose_name_plural = _('Invoices')
#         indexes = [
#             models.Index(fields=['cash_account']),
#             models.Index(fields=['receivable_account']),
#             models.Index(fields=['payable_account']),
#             models.Index(fields=['earnings_account']),
#             models.Index(fields=['created']),
#             models.Index(fields=['updated']),
#         ]
#
#     def __str__(self):
#         return f'Invoice: {self.invoice_number}'
#
#     def get_absolute_url(self, entity_slug):
#         return reverse('django_ledger:invoice-detail',
#                        kwargs={
#                            'entity_slug': entity_slug,
#                            'invoice_slug': self.invoice_number
#                        })
#
#     def get_migrate_state_desc(self):
#         """
#         Must be implemented.
#         :return:
#         """
#         return f'Invoice {self.invoice_number} account adjustment.'
#
#     def clean(self):
#         if not self.invoice_number:
#             self.invoice_number = generate_invoice_number()
#         super().clean()
