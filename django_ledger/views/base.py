from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import RedirectView, ListView

from django_ledger.models.entity import EntityModel


class RootUrlView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return reverse('django_ledger:login')
        return reverse('django_ledger:home')


class HomeView(ListView):
    template_name = 'django_ledger/home.html'
    PAGE_TITLE = _('My Entities')
    context_object_name = 'entities'
    extra_context = {
        'page_title': PAGE_TITLE,
        'header_title': PAGE_TITLE
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['header_subtitle'] = self.request.user.get_full_name
        context['header_subtitle_icon'] = 'ei:user'
        return context

    def get_queryset(self):
        return EntityModel.objects.for_user(
            user_model=self.request.user
        )
