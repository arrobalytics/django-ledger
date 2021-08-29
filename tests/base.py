from datetime import datetime
from logging import getLogger, DEBUG
from random import randint, choice

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django.test.client import Client
from django.utils.timezone import get_default_timezone

UserModel = get_user_model()


class DjangoLedgerBaseTest(TestCase):

    def setUp(self) -> None:

        self.logger = getLogger(__name__)
        self.logger.setLevel(level=DEBUG)

        self.USERNAME: str = 'testuser'
        self.PASSWORD: str = 'TestingDJL1234'
        self.USER_EMAIL: str = 'testuser@djangoledger.com'
        self.N: int = 5

        self.DAYS_FWD: int = randint(180, 180 * 3)
        self.TZ = get_default_timezone()
        self.START_DATE = self.get_random_date()

        self.CLIENT = Client(enforce_csrf_checks=True)

        try:
            self.user_model = UserModel.objects.get(username=self.USERNAME)
        except ObjectDoesNotExist:
            self.user_model = UserModel.objects.create_user(
                username=self.USERNAME,
                password=self.PASSWORD,
                email=self.USER_EMAIL,
            )

    def get_random_date(self) -> datetime:
        return datetime(
            year=choice(range(1990, 2020)),
            month=choice(range(1, 13)),
            day=choice(range(1, 28)),
            tzinfo=self.TZ
        )

    def login_client(self):
        return self.CLIENT.login(username=self.USERNAME, password=self.PASSWORD)

    def logout_client(self):
        self.CLIENT.logout()
