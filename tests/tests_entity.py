from datetime import datetime, date
from logging import getLogger, INFO
from random import choice, randint
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django.test.client import Client
from django.urls import reverse
from django.utils.timezone import get_default_timezone, localdate

from django_ledger.models import EntityModel
from django_ledger.settings import DJANGO_LEDGER_LOGIN_URL
from django_ledger.urls.entity import urlpatterns
from django_ledger.utils import populate_default_coa, generate_sample_data

UserModel = get_user_model()

logger = getLogger(__name__)
logger.setLevel(level=INFO)


class EntityModelTests(TestCase):

    def setUp(self) -> None:
        self.ENTITY_URL_PATTERN = {
            p.name: set(p.pattern.converters.keys()) for p in urlpatterns
        }
        self.USERNAME: str = 'testuser'
        self.PASSWORD: str = 'TestingDJL1234'
        self.USER_EMAIL: str = 'testuser@djangoledger.com'
        self.N: int = 5

        self.DAYS_FWD: int = randint(180, 180 * 3)
        self.TZ = get_default_timezone()
        self.START_DATE = self.get_random_date()

        self.CLIENT = Client()

        try:
            self.user_model = UserModel.objects.get(username=self.USERNAME)
        except ObjectDoesNotExist:
            self.user_model = UserModel.objects.create_user(
                username=self.USERNAME,
                password=self.PASSWORD,
                email=self.USER_EMAIL,
            )

        self.TEST_DATA = [self.get_random_entity_data() for _ in range(self.N)]

    @staticmethod
    def get_random_entity_data() -> dict:
        return {
            'name': f'Testing Inc-{randint(100000, 999999)}',
            'address_1': f'{randint(100000, 999999)} Main St',
            'address_2': f'Suite {randint(1000, 9999)}',
            'city': 'Charlotte',
            'state': 'NC',
            'zip_code': '28202',
            'country': 'US',
            'email': 'mytest@testinginc.com',
            'website': 'http://www.mytestingco.com',
        }

    def get_random_date(self) -> datetime:
        return datetime(
            year=choice(range(1990, 2020)),
            month=choice(range(1, 13)),
            day=choice(range(1, 28)),
            tzinfo=self.TZ
        )

    def login_client(self):
        return self.CLIENT.login(username=self.USERNAME, password=self.PASSWORD)

    def test_protected_views(self, test_date: date = None):
        """
        All Entity Model views must have user authenticated.
        If not, user must be redirected to login page.
        @param test_date: Optional test date. If None, will generate random date.
        """
        self.CLIENT.logout()
        entity_model_qs = EntityModel.objects.for_user(self.user_model)

        for entity_model in entity_model_qs:
            for path, kwargs in self.ENTITY_URL_PATTERN.items():
                url_kwargs = dict()
                if 'entity_slug' in kwargs:
                    url_kwargs['entity_slug'] = entity_model.slug
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

                self.assertEqual(response.status_code, 302,
                                 msg='EntityModelListView is not protected.')
                self.assertEqual(redirect_path, login_path,
                                 msg='EntityModelListView not redirecting to correct auth URL.')

    def test_entity_views(self):
        """
        Testing the creation of a number of entities.
        """
        # ENTITY-CREATE VIEW...
        entity_create_url = reverse('django_ledger:entity-create')
        response = self.CLIENT.get(entity_create_url, follow=False)

        # making sure user is logged in...
        if response.status_code == 302:
            self.login_client()
            response = self.CLIENT.get(entity_create_url)
            self.assertContains(response, status_code=200, text='New Entity Information')

        # checks that form throws Validation Error if any value is missing...
        entity_must_have_all = ['city', 'state', 'zip_code', 'country']
        for ent_data in self.TEST_DATA:
            while entity_must_have_all:
                ent_copy = ent_data.copy()
                del ent_copy[entity_must_have_all.pop()]
                response = self.CLIENT.post(entity_create_url, data=ent_copy, follow=False)
                self.assertContains(response, status_code=200, text='New Entity Information')
                self.assertFormError(response, form='form', field=None,
                                     errors='Must provide all City/State/Zip/Country')

        # checks that valid url is provided...
        ent_copy = self.get_random_entity_data()
        ent_copy['website'] = ent_copy['website'][1:]
        response = self.CLIENT.post(entity_create_url, data=ent_copy)
        self.assertFormError(response, form='form', field='website', errors='Enter a valid URL.')

        # checks that a valid entity name is provided...
        ent_copy = self.get_random_entity_data()
        ent_copy['name'] = ''
        response = self.CLIENT.post(entity_create_url, data=ent_copy, follow=False)
        self.assertFormError(response, form='form', field='name', errors='Please provide a valid name for new Entity.')

        # checks for valid entity name length....
        ent_copy = self.get_random_entity_data()
        ent_copy['name'] = 'In'
        response = self.CLIENT.post(entity_create_url, data=ent_copy, follow=False)
        self.assertFormError(response, form='form', field='name', errors='Looks like this entity name is too short...')

        # creating a number of entities...
        for ent_data in self.TEST_DATA:
            response = self.CLIENT.post(entity_create_url, data=ent_data, follow=True)
            # user must be redirected if success...
            self.assertContains(response, status_code=200, text='My Entities')
            self.assertContains(response, status_code=200, text=ent_data['name'])

        # ENTITY-LIST VIEW...
        with self.assertNumQueries(3):
            entity_list_url = reverse('django_ledger:entity-list')
            response = self.CLIENT.get(entity_list_url)

            # checks if it was able to render template...
            self.assertContains(response, status_code=200, text='My Entities')

            # checks if all entities where rendered...
            for ent_data in self.TEST_DATA:
                self.assertContains(response, status_code=200, text=ent_data['name'])

            # checks if all entities have proper anchor tags to dashboard and update views...
            entity_qs = response.context['entities']
            for entity_model in entity_qs:
                # checks if entity shows up in the list...
                self.assertContains(response,
                                    status_code=200,
                                    text=entity_model.name,
                                    msg_prefix=f'Entity {entity_model.name} not in the view!')

                # checks if there is a button with a link to the dashboard...
                self.assertContains(response,
                                    status_code=200,
                                    text=reverse('django_ledger:entity-detail',
                                                 kwargs={
                                                     'entity_slug': entity_model.slug
                                                 }))
                # checks if there is a button with a link to the update view...
                self.assertContains(response,
                                    status_code=200,
                                    text=reverse('django_ledger:entity-update',
                                                 kwargs={
                                                     'entity_slug': entity_model.slug
                                                 }))

        # ENTITY-UPDATE VIEW...
        with self.assertNumQueries(3):
            entity_model = entity_qs.first()
            entity_update_url = reverse('django_ledger:entity-update',
                                        kwargs={
                                            'entity_slug': entity_model.slug
                                        })
            response = self.CLIENT.get(entity_update_url)

        with self.assertNumQueries(5):
            # idea: DJL-123 - Chart of Accounts OneToOne Field on CoA Model?
            ent_data = response.context['form'].initial
            ent_data['name'] = 'New Cool Name LLC'
            ent_data = {k: v for k, v in ent_data.items() if v}
            response = self.CLIENT.post(entity_update_url, data=ent_data)

        with self.assertNumQueries(3):
            # redirects to entity list
            self.assertRedirects(response, expected_url=entity_list_url)

        with self.assertNumQueries(3):
            response = self.CLIENT.get(entity_list_url)
            # checks if updated entity is in list...
            self.assertContains(response, status_code=200, text=ent_data['name'])

        # ENTITY-DETAIL VIEW...
        entity_model = entity_model.get_previous_by_created()
        logger.warning(f'Populating CoA for {entity_model.name}...')
        # populates accounts with DJL default CoA.
        populate_default_coa(
            entity_model=entity_model,
            activate_accounts=True
        )

        logger.warning(f'Generating sample data for {entity_model.name}...')
        # generates sample data to perform tests.
        generate_sample_data(
            entity=entity_model,
            user_model=self.user_model,
            start_dt=self.START_DATE,
            days_fw=self.DAYS_FWD,
            tx_quantity=int(self.DAYS_FWD * 0.5)
        )

        with self.assertNumQueries(2):
            # this will redirect to entity-detail-month...
            entity_detail_url = reverse('django_ledger:entity-detail',
                                        kwargs={
                                            'entity_slug': entity_model.slug
                                        })
            response = self.CLIENT.get(entity_detail_url)

        with self.assertNumQueries(9):
            local_dt = localdate()
            entity_month_detail_url = reverse('django_ledger:entity-detail-month',
                                              kwargs={
                                                  'entity_slug': entity_model.slug,
                                                  'year': local_dt.year,
                                                  'month': local_dt.month
                                              })
            self.assertRedirects(response, entity_month_detail_url)

        with self.assertNumQueries(6):
            # same as before, but this time the session must not be update because user has not suited entities...
            response = self.CLIENT.get(entity_month_detail_url)
            self.assertContains(response, text=entity_model.name)
            self.assertTrue(response.context['bills'].count() >= 0)
            self.assertTrue(response.context['invoices'].count() >= 0)

        # ENTITY-DELETE VIEW...
        with self.assertNumQueries(3):
            entity_delete_url = reverse('django_ledger:entity-delete',
                                        kwargs={
                                            'entity_slug': entity_model.slug
                                        })
            response = self.CLIENT.get(entity_delete_url)
            self.assertContains(response,
                                status_code=200,
                                text=entity_model.name)
            self.assertContains(response,
                                status_code=200,
                                text=f'Are you sure you want to delete')
            self.assertContains(response,
                                status_code=200,
                                text=entity_delete_url)

        # this is a complex operation that requires several queries...
        response = self.CLIENT.post(entity_delete_url,
                                    data={
                                        'slug': entity_model.slug
                                    })
        with self.assertNumQueries(3):
            # checks that user is redirected to home after entity is deleted...
            home_url = reverse('django_ledger:home')
            self.assertRedirects(response, home_url)

        with self.assertNumQueries(3):
            # checks that entity no longer shows in entity list...
            response = self.CLIENT.get(entity_list_url)
            self.assertNotContains(response, text=entity_model.name)
