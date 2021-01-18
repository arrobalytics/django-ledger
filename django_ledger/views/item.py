from django.contrib.messages import add_message, ERROR
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView

from django_ledger.forms.item import (
    ProductOrServiceCreateForm, UnitOfMeasureModelCreateForm, UnitOfMeasureModelUpdateForm, ProductOrServiceUpdateForm
)
from django_ledger.models import ItemModel, UnitOfMeasureModel, EntityModel


class UnitOfMeasureModelListView(ListView):
    template_name = 'django_ledger/uom_list.html'
    PAGE_TITLE = _('Unit of Measures')
    context_object_name = 'uom_list'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'carbon:circle-measurement'
    }

    def get_queryset(self):
        return UnitOfMeasureModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )


class UnitOfMeasureModelCreateView(CreateView):
    template_name = 'django_ledger/uom_create.html'
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


class UnitOfMeasureModelUpdateView(UpdateView):
    template_name = 'django_ledger/uom_update.html'
    PAGE_TITLE = _('Update Unit of Measure')
    context_object_name = 'uom'
    slug_url_kwarg = 'uom_pk'
    slug_field = 'uuid'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'carbon:circle-measurement'
    }

    def get_queryset(self):
        return UnitOfMeasureModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

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


class ProductsAndServicesListView(ListView):
    template_name = 'django_ledger/pns_list.html'
    PAGE_TITLE = _('Products & Services')
    context_object_name = 'pns_list'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_queryset(self, **kwargs):
        return ItemModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )


class ProductOrServiceCreateView(CreateView):
    template_name = 'django_ledger/product_create.html'
    model = ItemModel
    PAGE_TITLE = _('Create New Product or Service')
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_success_url(self):
        return reverse('django_ledger:item-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })

    def get_form(self, form_class=None):
        return ProductOrServiceCreateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def form_valid(self, form):
        instance: ItemModel = form.save(commit=False)
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
        instance.save()
        return super().form_valid(form=form)


class ProductOrServiceUpdateView(UpdateView):
    template_name = 'django_ledger/product_update.html'
    PAGE_TITLE = _('Update Product or Service')
    context_object_name = 'item'
    slug_field = 'uuid'
    slug_url_kwarg = 'item_pk'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
        'header_subtitle_icon': 'zmdi:collection-item'
    }

    def get_queryset(self):
        return ItemModel.objects.for_entity(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user
        )

    def get_form(self, form_class=None):
        return ProductOrServiceUpdateForm(
            entity_slug=self.kwargs['entity_slug'],
            user_model=self.request.user,
            **self.get_form_kwargs()
        )

    def get_success_url(self):
        return reverse('django_ledger:item-list',
                       kwargs={
                           'entity_slug': self.kwargs['entity_slug']
                       })
