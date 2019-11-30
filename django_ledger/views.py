from django.db.models import Q
from django.db.models import Value, CharField
from django.views.generic import ListView, DetailView

from django_ledger.models.entity import EntityModel


class EntityModelListView(ListView):
    template_name = 'django_ledger/entities.html'
    context_object_name = 'entities'

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The View queryset.
        """
        owned = EntityModel.objects.filter(
            admin=self.request.user).annotate(
            user_role=Value('owned', output_field=CharField())
        )
        managed = EntityModel.objects.filter(entity_permissions__user=self.request.user).annotate(
            user_role=Value('managed', output_field=CharField())
        )
        return owned.union(managed).distinct()


class EntityModelDetailVew(DetailView):
    template_name = 'django_ledger/entity_detail.html'
    slug_url_kwarg = 'entity_slug'
    context_object_name = 'entity'

    def get_queryset(self):
        """
        Returns a queryset of all Entities owned or Managed by the User.
        Queryset is annotated with user_role parameter (owned/managed).
        :return: The view queryset.
        """
        return EntityModel.objects.filter(
            Q(admin=self.request.user) |
            Q(entity_permissions__user=self.request.user)
        )
