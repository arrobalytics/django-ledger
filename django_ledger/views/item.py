from django.contrib.messages import add_message, ERROR
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import RestrictedError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from django_ledger.forms.item import (
    ProductCreateForm, UnitOfMeasureModelCreateForm, UnitOfMeasureModelUpdateForm, ProductUpdateForm,
    ExpenseItemCreateForm, ExpenseItemUpdateForm, InventoryItemCreateForm, InventoryItemUpdateForm,
    ServiceCreateForm, ServiceUpdateForm
)
from django_ledger.models import ItemModel, UnitOfMeasureModel, EntityModel
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


# todo: Create delete views...

# UNIT OF MEASURE VIEWS....
class UnitOfMeasureModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if self.queryset is None:
            self.queryset = UnitOfMeasureModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            )
        return super().get_queryset()


class UnitOfMeasureModelListView(DjangoLedgerSecurityMixIn, UnitOfMeasureModelModelViewQuerySetMixIn, ListView):
    template_name = 'django_ledger/uom/uom_list.html'
    PAGE_TITLE = _('Unit of Measures')
    context_object_name = 'uom_list'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'carbon:circle-measurement'
    }


class UnitOfMeasureModelCreateView(DjangoLedgerSecurityMixIn, UnitOfMeasureModelModelViewQuerySetMixIn, CreateView):
    template_name = 'django_ledger/uom/uom_create.html'
    PAGE_TITLE = _('Create Unit of Measure')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'carbon:circle-measurement'
    }

    def get_success_url(self):
        return reverse('django_ledger:uom-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_form(self, form_class=None):
        return UnitOfMeasureModelCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        instance: UnitOfMeasureModel = form.save(commit=False)
        entity_slug = self.kwargs['entity_slug']
        try:
            entity_model: EntityModel = EntityModel.objects.for_user(
                user_model=self.request.user
            ).get(slug__iexact=entity_slug)
            instance.entity = entity_model
        except ObjectDoesNotExist:
            add_message(self.request,
                        level=ERROR,
                        message=_(f'User {self.request.user.username} cannot access entity {entity_slug}.'),
                        extra_tags='is-danger')
        else:
            try:
                instance.save()
            except IntegrityError:
                unit_abbr = form.cleaned_data['unit_abbr']
                add_message(self.request,
                            level=ERROR,
                            message=_(
                                f'The Unit of Measure {unit_abbr} already created for Entity {entity_model.name}.'),
                            extra_tags='is-danger')
                return self.render_to_response(self.get_context_data(form=form))
        return super().form_valid(form)


class UnitOfMeasureModelUpdateView(DjangoLedgerSecurityMixIn, UnitOfMeasureModelModelViewQuerySetMixIn, UpdateView):
    template_name = 'django_ledger/uom/uom_update.html'
    PAGE_TITLE = _('Update Unit of Measure')
    context_object_name = 'uom'
    slug_url_kwarg = 'uom_pk'
    slug_field = 'uuid'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'carbon:circle-measurement'
    }

    def get_success_url(self):
        return reverse('django_ledger:uom-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_form(self, form_class=None):
        return UnitOfMeasureModelUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )


class UnitOfMeasureModelDeleteView(DjangoLedgerSecurityMixIn, UnitOfMeasureModelModelViewQuerySetMixIn, DeleteView):
    pk_url_kwarg = 'uom_pk'
    template_name = 'django_ledger/uom/uom_delete.html'
    context_object_name = 'uom_model'

    def form_valid(self, form):
        try:
            return super(UnitOfMeasureModelDeleteView, self).form_valid(form)
        except RestrictedError:

            uom_model: UnitOfMeasureModel = self.object
            add_message(self.request,
                        level=ERROR,
                        message=f'Unable to delete UOM {uom_model.name}. '
                                'Remove dependencies before deleting.',
                        extra_tags='is-danger')

            return HttpResponseRedirect(
                redirect_to=reverse('django_ledger:uom-list',
                                    kwargs={
                                        'entity_slug': self.kwargs['entity_slug']
                                    })
            )

    def get_success_url(self):
        return reverse('django_ledger:uom-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


# PRODUCTS VIEWS...
class ProductItemModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if not self.queryset:
            self.queryset = ItemModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).products().select_related(
                'earnings_account', 'cogs_account',
                'inventory_account', 'uom').order_by('-updated')
        return super().get_queryset()


class ProductListView(DjangoLedgerSecurityMixIn,
                      ProductItemModelModelViewQuerySetMixIn,
                      ListView):
    template_name = 'django_ledger/product/product_list.html'
    PAGE_TITLE = _('Products')
    context_object_name = 'product_list'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }


class ProductCreateView(DjangoLedgerSecurityMixIn,
                        ProductItemModelModelViewQuerySetMixIn,
                        CreateView):
    template_name = 'django_ledger/product/product_create.html'
    model = ItemModel
    PAGE_TITLE = _('Create New Product')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_success_url(self):
        return reverse('django_ledger:product-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_form(self, form_class=None):
        return ProductCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        entity_slug = self.kwargs['entity_slug']
        entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user)
        entity_model = get_object_or_404(entity_model_qs, slug__exact=entity_slug)
        item_model: ItemModel = form.save(commit=False)
        item_model.entity = entity_model
        item_model.item_role = ItemModel.ITEM_ROLE_PRODUCT
        return super().form_valid(form=form)


class ProductUpdateView(DjangoLedgerSecurityMixIn,
                        ProductItemModelModelViewQuerySetMixIn,
                        UpdateView):
    template_name = 'django_ledger/product/product_update.html'
    PAGE_TITLE = _('Update Product')
    context_object_name = 'item'
    pk_url_kwarg = 'item_pk'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_queryset(self):
        return ItemModel.objects.products(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_form(self, form_class=None):
        return ProductUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:product-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


class ProductDeleteView(DjangoLedgerSecurityMixIn,
                        ProductItemModelModelViewQuerySetMixIn,
                        DeleteView):
    template_name = 'django_ledger/product/product_delete.html'
    pk_url_kwarg = 'item_pk'
    context_object_name = 'item_model'

    def form_valid(self, form):
        try:
            # todo: add success message...
            return super(ProductDeleteView, self).form_valid(form)
        except RestrictedError:

            item_model: ItemModel = self.object
            add_message(self.request,
                        level=ERROR,
                        message=f'Unable to delete Product or Service {item_model.name}. '
                                'Remove dependencies before deleting.',
                        extra_tags='is-danger')

            return HttpResponseRedirect(
                redirect_to=reverse('django_ledger:product-list',
                                    kwargs={
                                        'entity_slug': self.kwargs['entity_slug']
                                    })
            )

    def get_success_url(self):
        return reverse('django_ledger:product-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


# SERVICES VIEWS...
class ServiceItemModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if not self.queryset:
            self.queryset = ItemModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).services().select_related(
                'earnings_account', 'cogs_account',
                'inventory_account', 'uom').order_by('-updated')
        return super().get_queryset()


class ServiceListView(DjangoLedgerSecurityMixIn,
                      ServiceItemModelModelViewQuerySetMixIn,
                      ListView):
    template_name = 'django_ledger/service/service_list.html'
    PAGE_TITLE = _('Services')
    context_object_name = 'service_list'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }


class ServiceCreateView(DjangoLedgerSecurityMixIn,
                        ServiceItemModelModelViewQuerySetMixIn,
                        CreateView):
    template_name = 'django_ledger/service/service_create.html'
    model = ItemModel
    PAGE_TITLE = _('Create New Service')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_success_url(self):
        return reverse('django_ledger:service-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_form(self, form_class=None):
        return ServiceCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        entity_slug = self.kwargs['entity_slug']
        entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user)
        entity_model = get_object_or_404(entity_model_qs, slug__exact=entity_slug)
        item_model: ItemModel = form.save(commit=False)
        item_model.entity = entity_model
        return super().form_valid(form=form)


class ServiceUpdateView(DjangoLedgerSecurityMixIn,
                        ServiceItemModelModelViewQuerySetMixIn,
                        UpdateView):
    template_name = 'django_ledger/service/service_update.html'
    PAGE_TITLE = _('Update Service')
    context_object_name = 'item'
    pk_url_kwarg = 'item_pk'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_queryset(self):
        return ItemModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        ).services()

    def get_form(self, form_class=None):
        return ServiceUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:service-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


class ServiceDeleteView(DjangoLedgerSecurityMixIn,
                        ServiceItemModelModelViewQuerySetMixIn,
                        DeleteView):
    template_name = 'django_ledger/service/service_delete.html'
    pk_url_kwarg = 'item_pk'
    context_object_name = 'item_model'

    def form_valid(self, form):
        try:
            # todo: add success message...
            return super(ServiceDeleteView, self).form_valid(form)
        except RestrictedError:

            item_model: ItemModel = self.object
            add_message(self.request,
                        level=ERROR,
                        message=f'Unable to delete Product or Service {item_model.name}. '
                                'Remove dependencies before deleting.',
                        extra_tags='is-danger')

            return HttpResponseRedirect(
                redirect_to=reverse('django_ledger:service-list',
                                    kwargs={
                                        'entity_slug': self.kwargs['entity_slug']
                                    })
            )

    def get_success_url(self):
        return reverse('django_ledger:service-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


# EXPENSE ITEMS VIEW...

class ExpenseItemItemModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if not self.queryset:
            self.queryset = ItemModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).expenses().select_related('expense_account', 'uom').order_by('-updated')
        return super().get_queryset()


class ExpenseItemModelListView(DjangoLedgerSecurityMixIn, ExpenseItemItemModelModelViewQuerySetMixIn, ListView):
    template_name = 'django_ledger/expense/expense_list.html'
    PAGE_TITLE = _('Expense Items')
    context_object_name = 'expense_list'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }


class ExpenseItemCreateView(DjangoLedgerSecurityMixIn, ExpenseItemItemModelModelViewQuerySetMixIn, CreateView):
    template_name = 'django_ledger/expense/expense_create.html'
    model = ItemModel
    PAGE_TITLE = _('Create New Expense Item')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_success_url(self):
        return reverse('django_ledger:expense-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_form(self, form_class=None):
        return ExpenseItemCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        entity_slug = self.kwargs['entity_slug']
        entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user)
        entity_model = get_object_or_404(entity_model_qs, slug__exact=entity_slug)
        item_model: ItemModel = form.save(commit=False)
        item_model.entity = entity_model
        item_model.item_role = ItemModel.ITEM_ROLE_EXPENSE
        return super().form_valid(form=form)


class ExpenseItemUpdateView(DjangoLedgerSecurityMixIn, ExpenseItemItemModelModelViewQuerySetMixIn, UpdateView):
    template_name = 'django_ledger/expense/expense_update.html'
    PAGE_TITLE = _('Update Expense Item')
    context_object_name = 'item'
    slug_field = 'uuid'
    slug_url_kwarg = 'item_pk'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_form(self, form_class=None):
        return ExpenseItemUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:expense-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })


# INVENTORY VIEWS...

class InventoryItemItemModelModelViewQuerySetMixIn:
    queryset = None

    def get_queryset(self):
        if not self.queryset:
            self.queryset = ItemModel.objects.for_entity(
                entity_slug=self.kwargs['entity_slug'],
                user_model=self.request.user
            ).inventory_wip().select_related('inventory_account', 'cogs_account', 'uom').order_by('-updated')
        return super().get_queryset()


class InventoryItemModelListView(DjangoLedgerSecurityMixIn, InventoryItemItemModelModelViewQuerySetMixIn, ListView):
    template_name = 'django_ledger/inventory/inventory_item_list.html'
    PAGE_TITLE = _('Inventory Items')
    context_object_name = 'inventory_item_list'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }


class InventoryItemCreateView(DjangoLedgerSecurityMixIn, InventoryItemItemModelModelViewQuerySetMixIn, CreateView):
    template_name = 'django_ledger/inventory/inventory_item_create.html'
    model = ItemModel
    PAGE_TITLE = _('Create New Inventory Item')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_success_url(self):
        return reverse('django_ledger:inventory-item-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_form(self, form_class=None):
        return InventoryItemCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def form_invalid(self, form):
        """If the form is invalid, render the invalid form."""
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        entity_slug = self.kwargs['entity_slug']
        entity_model_qs = EntityModel.objects.for_user(user_model=self.request.user)
        entity_model = get_object_or_404(entity_model_qs, slug__exact=entity_slug)
        item_model: ItemModel = form.save(commit=False)
        item_model.entity = entity_model
        item_model.item_role = ItemModel.ITEM_ROLE_INVENTORY
        return super().form_valid(form=form)


class InventoryItemUpdateView(DjangoLedgerSecurityMixIn, InventoryItemItemModelModelViewQuerySetMixIn, UpdateView):
    template_name = 'django_ledger/inventory/inventory_item_update.html'
    PAGE_TITLE = _('Update Inventory Item')
    context_object_name = 'item'
    slug_field = 'uuid'
    slug_url_kwarg = 'item_pk'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_form(self, form_class=None):
        return InventoryItemUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:inventory-item-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })
