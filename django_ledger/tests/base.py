from datetime import datetime
from logging import getLogger, DEBUG
from random import randint, choice

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django.test.client import Client
from django.utils.timezone import get_default_timezone

from django_ledger.io.data_generator import EntityDataGenerator
from django_ledger.models import EntityModel

UserModel = get_user_model()


class DjangoLedgerBaseTest(TestCase):

    def setUp(self) -> None:

        self.logger = getLogger(__name__)
        self.logger.setLevel(level=DEBUG)

        self.USERNAME: str = 'testuser'
        self.PASSWORD: str = 'NeverUseThisPassword12345'
        self.USER_EMAIL: str = 'testuser@djangoledger.com'
        self.N: int = 3

        self.DAYS_FWD: int = randint(180, 180 * 3)
        self.TZ = get_default_timezone()
        self.START_DATE = self.get_random_date()

        self.CLIENT = Client(enforce_csrf_checks=False)

        try:
            self.user_model = UserModel.objects.get(username=self.USERNAME)
        except ObjectDoesNotExist:
            self.user_model = UserModel.objects.create_user(
                username=self.USERNAME,
                password=self.PASSWORD,
                email=self.USER_EMAIL,
            )

        self.TZ = get_default_timezone()
        self.START_DATE = self.get_random_date()
        self.FY_STARTS = [
            '1',
            '2',
            '3',
            '4',
            '5',
            '6',
            '7',
            '8',
            '9',
            '10',
            '11',
            '12'
        ]
        self.TEST_DATA = list()
        self.CAPITAL_CONTRIBUTION = 50000
        self.ENTITY_MODEL_QUERYSET = None

        self.create_entity_models(n=self.N)
        self.populate_entity_models()

    def get_random_date(self) -> datetime:
        return datetime(
            year=choice(range(1990, 2020)),
            month=choice(range(1, 13)),
            day=choice(range(1, 28)),
            tzinfo=self.TZ
        )

    def login_client(self):
        return self.CLIENT.login(
            username=self.USERNAME,
            password=self.PASSWORD
        )

    def logout_client(self):
        self.CLIENT.logout()

    def refresh_test_data(self, n: int = None):
        N = n if n else self.N
        self.TEST_DATA = [self.get_random_entity_data() for _ in range(N)]

    def get_random_entity_data(self) -> dict:
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
            'fy_start_month': choice(self.FY_STARTS)
        }

    def create_entity_models(self, save=True, n: int = 5):
        self.refresh_test_data(n)
        for ent_data in self.TEST_DATA:
            entity_model = EntityModel(**ent_data)
            entity_model.admin = self.user_model
            entity_model.clean()
            if save:
                entity_model.save()

    def populate_entity_models(self):
        entities_qs = EntityModel.objects.all()
        for entity_model in entities_qs:
            entity_model.populate_default_coa(activate_accounts=True)
            data_generator = EntityDataGenerator(
                user_model=self.user_model,
                entity_model=entity_model,
                start_date=self.START_DATE,
                capital_contribution=self.CAPITAL_CONTRIBUTION,
                days_forward=30 * 9,
                tx_quantity=50
            )
            self.logger.info(f'Populating Entity {entity_model.name}...')
            data_generator.populate_entity()
        self.ENTITY_MODEL_QUERYSET = entities_qs
