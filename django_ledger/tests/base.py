from datetime import date, timedelta
from decimal import Decimal
from itertools import cycle
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
    FY_STARTS = None
    CAPITAL_CONTRIBUTION = None
    START_DATE = None
    DAYS_FORWARD = 9 * 30
    TX_QUANTITY = 50
    user_model = None
    TEST_DATA = list()
    CLIENT = None
    TZ = None
    N = None
    USER_EMAIL = None
    PASSWORD = None
    USERNAME = None
    logger = None
    accrual_cycle = cycle([True, False])

    @classmethod
    def setUpTestData(cls):

        cls.logger = getLogger(__name__)
        cls.logger.setLevel(level=DEBUG)

        cls.USERNAME: str = 'testuser'
        cls.PASSWORD: str = 'NeverUseThisPassword12345'
        cls.USER_EMAIL: str = 'testuser@djangoledger.com'
        cls.N: int = 2

        cls.DAYS_FWD: int = randint(180, 180 * 3)
        cls.TZ = get_default_timezone()
        cls.START_DATE = cls.get_random_date()

        cls.CLIENT = Client(enforce_csrf_checks=False)

        try:
            cls.user_model = UserModel.objects.get(username=cls.USERNAME)
        except ObjectDoesNotExist:
            cls.user_model = UserModel.objects.create_user(
                username=cls.USERNAME,
                password=cls.PASSWORD,
                email=cls.USER_EMAIL,
            )

        cls.FY_STARTS = list(str(i) for i in range(1, 13))
        cls.TEST_DATA = list()
        cls.CAPITAL_CONTRIBUTION = Decimal('50000.00')
        cls.ENTITY_MODEL_QUERYSET = None

        cls.create_entity_models(n=cls.N)
        cls.populate_entity_models()

    @classmethod
    def get_random_date(cls) -> date:
        return date(
            year=choice(range(1990, 2020)),
            month=choice(range(1, 13)),
            day=choice(range(1, 28))
        )

    @classmethod
    def login_client(cls):
        cls.logger.info('Logging in client...')
        cls.CLIENT.login(
            username=cls.USERNAME,
            password=cls.PASSWORD
        )

    @classmethod
    def logout_client(cls):
        cls.logger.info('Logging out client...')
        cls.CLIENT.logout()

    @classmethod
    def refresh_test_data(cls, n: int = None):
        N = n if n else cls.N
        cls.TEST_DATA = [cls.get_random_entity_data() for _ in range(N)]

    @classmethod
    def get_random_entity_data(cls) -> dict:
        return {
            'slug': f'a-cool-slug-{randint(10000, 99999)}',
            'name': f'Testing Inc-{randint(100000, 999999)}',
            'address_1': f'{randint(100000, 999999)} Main St',
            'address_2': f'Suite {randint(1000, 9999)}',
            'city': 'Charlotte',
            'state': 'NC',
            'zip_code': '28202',
            'country': 'US',
            'email': 'mytest@testinginc.com',
            'website': 'http://www.mytestingco.com',
            'fy_start_month': choice(cls.FY_STARTS),
            'admin': cls.user_model,
            'accrual_method': next(cls.accrual_cycle)
        }

    def get_random_entity_model(self) -> EntityModel:
        if self.ENTITY_MODEL_QUERYSET:
            return choice(self.ENTITY_MODEL_QUERYSET)
        raise ValueError('EntityModels have not been populated.')

    @classmethod
    def create_entity_models(cls, save=True, n: int = 5):
        cls.refresh_test_data(n)
        for ent_data in cls.TEST_DATA:
            entity_model = EntityModel.add_root(**ent_data)
            entity_model.admin = cls.user_model
            entity_model.clean()
            if save:
                entity_model.save()

    @classmethod
    def populate_entity_models(cls):
        entities_qs = EntityModel.objects.all()
        for entity_model in entities_qs:
            data_generator = EntityDataGenerator(
                user_model=cls.user_model,
                entity_model=entity_model,
                start_date=cls.START_DATE,
                capital_contribution=cls.CAPITAL_CONTRIBUTION,
                days_forward=cls.DAYS_FORWARD,
                tx_quantity=cls.TX_QUANTITY
            )
            cls.logger.info(f'Populating Entity {entity_model.name}...')
            data_generator.populate_entity()
        cls.ENTITY_MODEL_QUERYSET = entities_qs

    def get_random_draft_date(self):
        return self.START_DATE + timedelta(days=randint(0, 365))
