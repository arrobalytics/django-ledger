from uuid import uuid4

from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import localtime

from django_ledger.admin.coa import ChartOfAccountsInLine
from django_ledger.models.entity import EntityModel, EntityManagementModel


class EntityManagementInLine(admin.TabularInline):
    model = EntityManagementModel


class EntityModelAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'accrual_method',
        'last_closing_date',
        'hidden',
        'get_coa_count',
        'add_ledger_link'
    ]
    readonly_fields = [
        'depth',
        'path',
        'numchild',
        'last_closing_date',
        'default_coa'
    ]
    fieldsets = [
        (
            'Entity Information', {
                'fields': [
                    'name',
                    'admin',
                    'fy_start_month',
                    'accrual_method',
                    'hidden',
                    'picture'
                ]
            }
        ),
        (
            'Contact Information', {
                'fields': [
                    'address_1',
                    'address_2',
                    'city',
                    'state',
                    'zip_code',
                    'email',
                    'website',
                    'phone'
                ]
            }
        ),
        (
            'Chart of Accounts', {
                'fields': [
                    'default_coa'
                ]
            }
        )
    ]
    inlines = [
        ChartOfAccountsInLine,
        EntityManagementInLine
    ]
    actions = [
        'add_code_of_accounts'
    ]

    class Meta:
        model = EntityModel

    def get_queryset(self, request):
        qs = super().get_queryset(request=request)
        qs = qs.annotate(Count('chartofaccountmodel'))
        if request.user.is_superuser:
            return qs
        return qs.for_user(user_model=request.user)

    def add_ledger_link(self, obj):
        add_ledger_url = reverse('admin:django_ledger_ledgermodel_add')
        return format_html('<a class="addlink" href="{url}?entity_slug={slug}">Add Ledger</a>',
                           url=add_ledger_url,
                           slug=obj.slug)

    def add_code_of_accounts(self, request, queryset):
        for entity_model in queryset:
            entity_model.create_chart_of_accounts(
                coa_name=f'{entity_model.name} CoA {localtime().isoformat()}',
                commit=True,
                assign_as_default=False
            )

    def get_coa_count(self, obj):
        return obj.chartofaccountmodel__count

    get_coa_count.short_description = 'CoA Count'

    def save_model(self, request, obj, form, change):
        if not change:
            if obj.uuid is None:
                obj.uuid = uuid4()
            EntityModel.add_root(instance=obj)
            return
        super().save_model(request, obj, form, change)
