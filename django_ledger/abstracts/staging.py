# import uuid
#
# from django.db import models
# from django.utils.translation import gettext_lazy as _
#
# from django_ledger.abstracts.mixins import CreateUpdateMixIn
#
#
# class ImportJobModelAbstract(CreateUpdateMixIn):
#     uuid = models.UUIDField(default=uuid.uuid4, primary_key=True, verbose_name=_('UUID'))
#     description = models.CharField(max_length=200, verbose_name=_('Description'))
#     entity = models.ForeignKey('django_ledger.EntityModel', on_delete=models.CASCADE, verbose_name=_('Entity'))
#     ledger = models.ForeignKey('django_ledger.LedgerModel', on_delete=models.CASCADE, verbose_name=_('Ledger'))
#
#     class Meta:
#         abstract = True
#         verbose_name = _('Import Job Model')
#         indexes = [
#             models.Index(fields=['entity']),
#             models.Index(fields=['ledger']),
#             models.Index(fields=['entity', 'ledger'])
#         ]
#
#
# class StagedTransactionModelAbstract(CreateUpdateMixIn):
#     import_job = models.ForeignKey('django_ledger.ImportJobModel',
#                                    on_delete=models.CASCADE)
#     earnings_account = models.ForeignKey('django_ledger.AccountModel',
#                                          on_delete=models.CASCADE,
#                                          null=True,
#                                          blank=True)
#
#     fitid = models.CharField(max_length=100)
#     amount = models.DecimalField(decimal_places=2, max_digits=15)
#     date_posted = models.DateField()
#
#     name = models.CharField(max_length=200, blank=True, null=True)
#     memo = models.CharField(max_length=200, blank=True, null=True)
#
#     tx = models.OneToOneField('django_ledger.TransactionModel',
#                               on_delete=models.SET_NULL,
#                               null=True,
#                               blank=True)
#
#     class Meta:
#         abstract = True
#         verbose_name = _('Staged Transaction Model')
#         indexes = [
#             models.Index(fields=['import_job'])
#         ]
