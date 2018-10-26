from django.contrib import admin

from books.models import LedgerModel, EntityModel


class EntityModelAdmin(admin.ModelAdmin):
    class Meta:
        model = EntityModel



class LedgerModelAdmin(admin.ModelAdmin):
    class Meta:
        model = LedgerModel


admin.site.register(EntityModel, EntityModelAdmin)
admin.site.register(LedgerModel, LedgerModelAdmin)
