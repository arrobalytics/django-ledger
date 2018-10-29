from django.contrib import admin

from django_ledger.models import LedgerModel, EntityModel, ChartOfAccountModel, AccountModel, CoAAccountAssignments


class EntityModelAdmin(admin.ModelAdmin):
    class Meta:
        model = EntityModel


# class CoAAccountThroughAdmin(admin.ModelAdmin):
#     list_filter = [
#         'coa',
#     ]
#
#     class Meta:
#         model = CoAAccountAssignments


class CoAAssignmentsInLine(admin.TabularInline):
    model = CoAAccountAssignments


class ChartOfAccountsModelAdmin(admin.ModelAdmin):
    inlines = [
        CoAAssignmentsInLine
    ]

    class Meta:
        model = CoAAccountAssignments


class AccountModelAdmin(admin.ModelAdmin):
    actions_on_top = True
    actions_on_bottom = True

    readonly_fields = [
        'role_bs',
        'role_bs_upper',
    ]
    list_display = [
        '__str__',
        'code',
        'parent'
    ]
    list_filter = [
        'role_bs',
        'balance_type',
    ]
    fieldsets = (
        ('Balance Sheet', {
            'fields': (
                'role_bs_upper',
            )
        }),
        ('Account', {
            'fields': (
                ('code', 'name'),
                'parent',
                ('role', 'balance_type')
            )
        }),
    )

    class Meta:
        model = AccountModel

    def role_bs_upper(self, acc):
        return acc.role_bs.upper()

    role_bs_upper.short_description = 'Balance Sheet Role'


class LedgerModelAdmin(admin.ModelAdmin):
    class Meta:
        model = LedgerModel


admin.site.register(EntityModel, EntityModelAdmin)
admin.site.register(LedgerModel, LedgerModelAdmin)
# admin.site.register(CoAAccountAssignments, CoAAccountThroughAdmin)
admin.site.register(ChartOfAccountModel, ChartOfAccountsModelAdmin)
admin.site.register(AccountModel, AccountModelAdmin)
