# from django.db import models
# from django.utils.translation import gettext_lazy as _
#
# from django_ledger.abstracts.mixins import CreateUpdateMixIn
#
#
# class FinancialInstitutionModelAbstract(CreateUpdateMixIn):
#     name = models.CharField(max_length=50)
#     entity = models.ForeignKey('django_ledger.EntityModel', on_delete=models.CASCADE)
#     ofx_fid = models.CharField(max_length=15, null=True, blank=True, unique=True)
#     ofx_org = models.CharField(max_length=50, null=True, blank=True)
#
#     class Meta:
#         abstract = True
#         verbose_name = _('Financial Institution')
#
#
# class FinancialInstitutionModel(FinancialInstitutionModelAbstract):
#     """
#     Bank Model Base Class
#     """
