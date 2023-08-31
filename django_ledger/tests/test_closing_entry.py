from random import choice
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.urls import reverse

from django_ledger.tests.base import DjangoLedgerBaseTest
from django_ledger.urls.closing_entry import urlpatterns as closing_entry_urls

UserModel = get_user_model()


class ClosingEntryModelTests(DjangoLedgerBaseTest):

    def setUp(self) -> None:
        self.URL_PATTERNS = {
            p.name: set(p.pattern.converters.keys()) for p in closing_entry_urls
        }

        for entity_model in self.ENTITY_MODEL_QUERYSET:
            for y in [self.START_DATE.year, self.START_DATE.year + 1]:
                for m in range(1, 13):
                    ce_model, ce_txs_list = entity_model.close_books_for_month(
                        year=y,
                        month=m,
                        force_update=True)

    def test_protected_views(self):
        self.logout_client()
        entity_model = self.get_random_entity_model()
        closing_entry_model = choice(entity_model.get_closing_entries())

        for path, kwargs in self.URL_PATTERNS.items():
            url_kwargs = dict()
            url_kwargs['entity_slug'] = entity_model.slug
            if 'year' in kwargs:
                url_kwargs['year'] = closing_entry_model.closing_date.year
            if 'month' in kwargs:
                url_kwargs['month'] = closing_entry_model.closing_date.month
            if 'closing_entry_pk' in kwargs:
                url_kwargs['closing_entry_pk'] = closing_entry_model.uuid

            url = reverse(f'django_ledger:{path}', kwargs=url_kwargs)
            response = self.CLIENT.get(url, follow=False)
            redirect_url = urlparse(response.url)
            redirect_path = redirect_url.path
            login_path = reverse(viewname='django_ledger:login')

            self.assertEqual(response.status_code, 302, msg=f'{path} view is not protected.')
            self.assertEqual(redirect_path, login_path, msg=f'{path} view not redirecting to correct auth URL.')

    def test_closing_entry_list(self):
        self.login_client()
        entity_model = self.get_random_entity_model()
        url = reverse('django_ledger:closing-entry-list', kwargs={'entity_slug': entity_model.slug})
        with self.assertNumQueries(5):
            response = self.CLIENT.get(path=url)

    def test_closing_entry_create(self):
        entity_model = self.get_random_entity_model()

        with self.assertNumQueries(1):

            # closing entry does not exist...
            entity_model.close_books_for_month(
                year=self.START_DATE.year + 2,
                month=self.START_DATE.month
            )
