from django.contrib.admin import TabularInline, ModelAdmin
from django.db.models import Count
from django.forms import ModelForm, BooleanField, BaseInlineFormSet

from django_ledger.models.accounts import AccountModel
from django_ledger.models.coa import ChartOfAccountModel
from django_ledger.models.entity import EntityModel


class AccountModelInLineForm(ModelForm):
    role_default = BooleanField(initial=False, required=False)

    class Meta:
        model = AccountModel
        fields = []


class AccountModelInLineFormSet(BaseInlineFormSet):

    def save_new(self, form, commit=True):
        setattr(form.instance, self.fk.name, self.instance)
        if commit:
            account_model = AccountModel.add_root(
                instance=super().save_new(form, commit=False)
            )
            return account_model
        return super().save_new(form, commit=False)


class AccountModelInLine(TabularInline):
    extra = 0
    form = AccountModelInLineForm
    formset = AccountModelInLineFormSet
    show_change_link = True
    exclude = [
        'path',
        'depth',
        'numchild'
    ]
    model = AccountModel
    fieldsets = [
        ('', {
            'fields': [
                'role',
                'balance_type',
                'code',
                'name',
                'role_default',
                'locked',
                'active'
            ]
        })
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.not_coa_root()


class ChartOfAccountsAdminForm(ModelForm):
    assign_as_default = BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.is_default():
            self.fields['assign_as_default'].initial = True
            self.fields['assign_as_default'].disabled = True

    def save(self, commit=True):
        if commit:
            if self.cleaned_data['assign_as_default']:
                entity_model: EntityModel = self.instance.entity
                entity_model.default_coa = self.instance
                entity_model.save(update_fields=[
                    'default_coa'
                ])
        return super().save(commit=commit)


class ChartOfAccountsInLine(TabularInline):
    form = ChartOfAccountsAdminForm
    model = ChartOfAccountModel
    extra = 0
    show_change_link = True
    fields = [
        'name',
        'locked',
        'assign_as_default'
    ]


class ChartOfAccountsModelAdmin(ModelAdmin):
    list_filter = [
        'entity__name',
        'locked'
    ]
    list_display = [
        'entity_name',
        'name',
        'slug',
        'locked',
        'account_model_count'
    ]
    search_fields = [
        'slug',
        'entity__name'
    ]
    list_display_links = ['name']
    fields = [
        'name',
        'locked',
        'description',
    ]
    inlines = [
        AccountModelInLine
    ]

    class Meta:
        model = ChartOfAccountModel

    def entity_name(self, obj):
        return obj.entity.name

    def get_queryset(self, request):
        qs = ChartOfAccountModel.objects.for_user(user_model=request.user)
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        qs = qs.select_related('entity').annotate(Count('accountmodel'))
        return qs

    def account_model_count(self, obj):
        return obj.accountmodel__count

    account_model_count.short_description = 'Accounts'