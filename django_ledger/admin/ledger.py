from django.contrib import messages
from django.contrib.admin import ModelAdmin, TabularInline
from django.db.models import Count
from django.forms import BaseInlineFormSet
from django.shortcuts import get_object_or_404
from django.utils.html import format_html

from django_ledger.models import (
    LedgerModel, JournalEntryModel, EntityModel,
    LedgerModelValidationError
)


class JournalEntryModelInLineFormSet(BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        self.ledger_model: LedgerModel = kwargs['instance']
        self.entity_model = self.ledger_model.entity
        super().__init__(*args, **kwargs)

    def add_fields(self, form, index):
        super().add_fields(form=form, index=index)
        form.fields['entity_unit'].queryset = self.entity_model.entityunitmodel_set.all()


class JournalEntryModelInLine(TabularInline):
    extra = 0
    fields = [
        'timestamp',
        'description',
        'entity_unit',
        'posted',
        'locked',
        'activity',
        'origin',
        'txs_count',
        'view_txs_link',
        'edit_txs_link'
    ]
    readonly_fields = [
        'posted',
        'locked',
        'origin',
        'activity',
        'txs_count',
        'view_txs_link',
        'edit_txs_link'
    ]
    model = JournalEntryModel
    formset = JournalEntryModelInLineFormSet

    def get_queryset(self, request):
        qs = self.model.objects.for_user(request.user)
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs.annotate(
            txs_count=Count('transactionmodel')
        ).select_related(
            'ledger',
            'ledger__entity'
        )

    def txs_count(self, obj):
        return obj.txs_count

    txs_count.short_description = 'Transactions'

    def has_change_permission(self, request, obj=None):
        if obj:
            return all([
                not obj.is_locked(),
                super().has_change_permission(request, obj)
            ])
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj:
            return all([
                obj.can_delete(),
                super().has_delete_permission(request, obj)
            ])
        return super().has_delete_permission(request, obj)

    def view_txs_link(self, obj: JournalEntryModel):
        detail_url = obj.get_detail_url()
        return format_html(
            format_string='<a class="viewlink" target="_blank" href="{url}">View Txs</a>',
            url=detail_url
        )

    def edit_txs_link(self, obj: JournalEntryModel):
        detail_url = obj.get_detail_txs_url()
        next_url = None
        return format_html(
            format_string='<a class="changelink" target="_blank" href="{url}">Edit Txs</a>',
            url=detail_url
        )


class LedgerModelAdmin(ModelAdmin):
    readonly_fields = [
        'entity',
        'posted',
        'locked'
    ]
    list_filter = [
        'posted',
        'locked'
    ]
    list_display = [
        'name',
        'is_posted',
        'is_locked',
        'is_extended',
        'journal_entry_count',
        'earliest_journal_entry'
    ]
    actions = [
        'post',
        'unpost',
        'lock',
        'unlock'
    ]
    inlines = [
        JournalEntryModelInLine
    ]

    def get_queryset(self, request):
        qs = LedgerModel.objects.for_user(user_model=request.user)
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs.select_related('entity')

    def get_inlines(self, request, obj):
        if obj is None:
            return []
        return super().get_inlines(request, obj)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return [
                ('', {
                    'fields': [
                        'name',
                        'hidden',
                        'additional_info'
                    ]
                })
            ]
        return [
            ('', {
                'fields': [
                    'entity',
                    'name',
                    'hidden',
                    'additional_info'
                ]
            })
        ]

    def get_entity_model(self, request) -> EntityModel:
        entity_slug = request.GET.get('entity_slug')
        entity_model_qs = EntityModel.objects.for_user(user_model=request.user)
        entity_model = get_object_or_404(entity_model_qs, slug__exact=entity_slug)
        return entity_model

    def has_add_permission(self, request):
        if request.GET.get('entity_slug') is not None:
            return True
        return False

    def add_view(self, request, form_url="", extra_context=None):
        entity_model = self.get_entity_model(request)
        extra_context = {
            'entity_model': entity_model,
            'title': f'Add Ledger: {entity_model.name}'
        }
        return super().add_view(request, form_url="", extra_context=extra_context)

    def is_locked(self, obj):
        return obj.is_locked()

    is_locked.boolean = True

    def is_posted(self, obj):
        return obj.is_posted()

    is_posted.boolean = True

    def is_extended(self, obj):
        return obj.has_wrapped_model()

    is_extended.boolean = True

    # ACTIONS....
    def post(self, request, queryset):
        for obj in queryset:
            try:
                obj.post(raise_exception=True, commit=False)
            except LedgerModelValidationError as e:
                messages.error(
                    request=request,
                    message=e.message
                )
        queryset.bulk_update(
            objs=queryset,
            fields=[
                'posted',
                'updated'
            ])

    def lock(self, request, queryset):
        for obj in queryset:
            try:
                obj.lock(raise_exception=True, commit=False)
            except LedgerModelValidationError as e:
                messages.error(
                    request=request,
                    message=e.message
                )

        queryset.bulk_update(
            objs=queryset,
            fields=[
                'locked',
                'updated'
            ])

    def unpost(self, request, queryset):
        for obj in queryset:
            try:
                obj.unpost(raise_exception=True, commit=False)
            except LedgerModelValidationError as e:
                messages.error(
                    request=request,
                    message=e.message
                )
        queryset.bulk_update(
            objs=queryset,
            fields=[
                'posted',
                'updated'
            ])

    def unlock(self, request, queryset):
        for obj in queryset:
            try:
                obj.unlock(raise_exception=True, commit=False)
            except LedgerModelValidationError as e:
                messages.error(
                    request=request,
                    message=e.message
                )

        queryset.bulk_update(
            objs=queryset,
            fields=[
                'locked',
                'updated'
            ])

    def journal_entry_count(self, obj):
        return obj.journal_entries__count

    def earliest_journal_entry(self, obj):
        return obj.earliest_timestamp

    def save_model(self, request, obj: LedgerModel, form, change):
        if not change:
            entity_model = self.get_entity_model(request)
            obj.entity = entity_model
        return super().save_model(
            request=request,
            obj=obj,
            form=form,
            change=change
        )

    class Meta:
        model = LedgerModel
