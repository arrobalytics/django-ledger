from django.contrib import admin

from django_ledger.admin.coa import ChartOfAccountsModelAdmin
from django_ledger.admin.entity import EntityModelAdmin
from django_ledger.admin.ledger import LedgerModelAdmin
from django_ledger.models import EntityModel, ChartOfAccountModel, LedgerModel

admin.site.register(EntityModel, EntityModelAdmin)
admin.site.register(ChartOfAccountModel, ChartOfAccountsModelAdmin)
admin.site.register(LedgerModel, LedgerModelAdmin)
