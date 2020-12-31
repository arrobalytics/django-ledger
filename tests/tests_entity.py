from datetime import datetime, date
from random import choice, randint

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.client import Client
from django.urls import reverse
from django.utils.timezone import get_default_timezone
from urllib.parse import urlparse

from django_ledger.models.entity import EntityModel
from django_ledger.utils import generate_sample_data, populate_default_coa
from django_ledger.urls.entity import urlpatterns
from django_ledger.settings import DJANGO_LEDGER_LOGIN_URL

UserModel = get_user_model()


class EntityModelTests(TestCase):
    """
    Entity Model URLs:

    path('list/', views.EntityModelListView.as_view(), name='entity-list'),
    path('create/', views.EntityModelCreateView.as_view(), name='entity-create'),

    path('<slug:entity_slug>/dashboard/',
         views.EntityDashboardView.as_view(),
         name='entity-dashboard'),
    path('<slug:entity_slug>/dashboard/year/<int:year>/',
         views.FiscalYearEntityModelDashboardView.as_view(),
         name='entity-dashboard-year'),
    path('<slug:entity_slug>/dashboard/quarter/<int:year>/<int:quarter>/',
         views.QuarterlyEntityDashboardView.as_view(),
         name='entity-dashboard-quarter'),
    path('<slug:entity_slug>/dashboard/month/<int:year>/<int:month>/',
         views.MonthlyEntityDashboardView.as_view(),
         name='entity-dashboard-month'),
    path('<slug:entity_slug>/dashboard/date/<int:year>/<int:month>/<int:day>/',
         views.DateEntityDashboardView.as_view(),
         name='entity-dashboard-date'),
    path('<slug:entity_slug>/update/', views.EntityModelUpdateView.as_view(), name='entity-update'),
    path('<slug:entity_slug>/delete/', views.EntityDeleteView.as_view(), name='entity-delete'),
    path('<slug:entity_slug>/set-date/', views.SetSessionDate.as_view(), name='entity-set-date'),
    path('set-default/', views.SetDefaultEntityView.as_view(), name='entity-set-default'),

    """

    def setUp(self) -> None:
        self.ENTITY_URL_PATTERN = {
            p.name: set(p.pattern.converters.keys()) for p in urlpatterns
        }
        self.USERNAME = 'testuser'
        self.PASSWORD = 'TestingDJL1234'
        self.ENTITY_NAME = 'My Test Corp'
        self.DAYS_FWD = randint(180, 180 * 3)

        self.TZ = get_default_timezone()
        self.START_DATE = self.get_random_date()

        self.CLIENT = Client(enforce_csrf_checks=True)

        self.user_model = UserModel.objects.create(
            username=self.USERNAME,
            password=self.PASSWORD
        )

        self.entity_model: EntityModel = EntityModel(
            name=self.ENTITY_NAME,
            admin=self.user_model
        )

        # Saves and makes sure the entity has a slug...
        self.entity_model.clean()
        self.entity_model.save()
        self.ENTITY_SLUG = self.entity_model.slug

        # populates accounts with DJL default CoA.
        populate_default_coa(
            entity_model=self.entity_model,
            activate_accounts=True
        )

        # generates sample data to perform tests.
        generate_sample_data(
            entity=self.entity_model,
            user_model=self.user_model,
            start_dt=self.START_DATE,
            days_fw=self.DAYS_FWD,
            tx_quantity=int(self.DAYS_FWD * 0.5)
        )

    def get_random_date(self):
        return datetime(
            year=choice(range(1990, 2020)),
            month=choice(range(1, 13)),
            day=choice(range(1, 28)),
            tzinfo=self.TZ
        )

    def login_client(self):
        self.CLIENT.login(username=self.USERNAME, password=self.PASSWORD)

    def test_protected_views(self, test_date: date = None):
        """
        All Entity Model views must have user authenticated.
        If not, user mut be redirected to login page.
        @param test_date: Optional test date. If None, will generate random date.
        """
        for path, kwargs in self.ENTITY_URL_PATTERN.items():
            url_kwargs = dict()
            if 'entity_slug' in kwargs:
                url_kwargs['entity_slug'] = self.ENTITY_SLUG
            if 'year' in kwargs:
                test_date = self.get_random_date()
                url_kwargs['year'] = test_date.year
            if 'month' in kwargs:
                url_kwargs['month'] = test_date.month
            if 'quarter' in kwargs:
                url_kwargs['quarter'] = choice(range(1, 5))
            if 'day' in kwargs:
                url_kwargs['day'] = test_date.day

            url = reverse(f'django_ledger:{path}', kwargs=url_kwargs)
            response = self.CLIENT.get(url, follow=False)
            redirect_url = urlparse(response.url)
            redirect_path = redirect_url.path
            login_path = DJANGO_LEDGER_LOGIN_URL

            self.assertEqual(response.status_code, 302, msg='EntityModelListView is not protected.')
            self.assertEqual(redirect_path, login_path, msg='EntityModelListView not redirecting to correct auth URL.')
