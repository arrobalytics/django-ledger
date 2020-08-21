from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import RedirectView, ListView

from django_ledger.models.entity import EntityModel


class RootUrlView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return reverse('django_ledger:login')
        return reverse('django_ledger:dashboard')


class DashboardView(ListView):
    template_name = 'django_ledger/dashboard.html'
    PAGE_TITLE = _('Dashboard')
    context_object_name = 'entities'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_queryset(self):
        return EntityModel.objects.for_user(
            user_model=self.request.user
        )
