"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Home / dashboard views.

  * RootUrlView — redirects anonymous users to login, others to home
  * DashboardView — lists entities the authenticated user is authorized for
"""

from typing import Optional

from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import RedirectView, ListView

from django_ledger.models.entity import EntityModelQuerySet
from django_ledger.views.mixins import DjangoLedgerSecurityMixIn


class RootUrlView(RedirectView):
    """Entry redirect: login if anonymous, otherwise the user dashboard."""

    def get_redirect_url(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return reverse('django_ledger:login')
        return reverse('django_ledger:home')


class DashboardModelBaseView(DjangoLedgerSecurityMixIn):
    """
    User-scoped entity queryset shared by the home dashboard.

    Reuses the security mixin's authorized-entity queryset so the dashboard
    never lists entities outside the current user's tenancy boundary.
    """

    queryset: Optional[EntityModelQuerySet] = None

    def get_queryset(self) -> EntityModelQuerySet:
        if self.queryset is None:
            qs: EntityModelQuerySet = self.get_authorized_entity_queryset()
            self.queryset = qs
        return self.queryset


# -----------------
# RETRIEVE (Dashboard)
# -----------------
class DashboardView(DashboardModelBaseView, ListView):
    """
    User home dashboard listing only entities the user may access
    (via get_authorized_entity_queryset — no cross-tenant leakage).
    """

    template_name = 'django_ledger/entity/home.html'
    PAGE_TITLE = _('My Dashboard')
    context_object_name = 'entities'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE,
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_subtitle'] = self.request.user.get_full_name()
        context['header_subtitle_icon'] = 'ei:user'
        return context
