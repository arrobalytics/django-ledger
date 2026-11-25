"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

Contributions to this module:
    * Miguel Sanda <msanda@arrobalytics.com>

Tests for running Django Ledger without the demo extra.

Faker is only installed with pip install "django-ledger[demo]". Without it the package must still import, the entity
create page must still work with the sample data option turned off, and every way of asking for sample data must end
in a clear message that names the demo extra instead of a server error or a half-created entity. These tests stand in
for a missing Faker by switching off the flags the package reads, so they run whether Faker is installed or not.
One test also imports the package in a separate Python process where importing Faker fails.
"""

import os
import subprocess
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from django_ledger.demo import FAKER_MISSING_MESSAGE
from django_ledger.forms.entity import EntityModelCreateForm
from django_ledger.io.io_core import get_localtime
from django_ledger.io.io_generator import EntityDataGenerator
from django_ledger.models import EntityModel, TransactionModel

UserModel = get_user_model()

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

GENERATOR_FAKER_FLAG: str = 'django_ledger.io.io_generator.FAKER_IMPORTED'
FORM_FAKER_FLAG: str = 'django_ledger.forms.entity.FAKER_INSTALLED'

DEMO_EXTRA: str = 'django-ledger[demo]'

NEW_ENTITY_POST_DATA: dict[str, str] = {
    'name': 'Demo Extra Entity',
    'address_1': '100 Main St',
    'address_2': '',
    'city': 'Charlotte',
    'state': 'NC',
    'zip_code': '28202',
    'country': 'US',
    'email': 'demo-extra@djangoledger.com',
    'website': 'https://www.djangoledger.com',
    'phone': '',
    'fy_start_month': '1',
    'accrual_method': 'on',
    'default_coa': 'on',
    'activate_all_accounts': 'on',
}

IMPORT_WITHOUT_FAKER_SCRIPT: str = """
import sys

sys.modules['faker'] = None

import django

django.setup()

import django_ledger.admin
import django_ledger.forms.entity
import django_ledger.io.io_generator
import django_ledger.urls
import django_ledger.views.entity
from django_ledger.demo import FAKER_INSTALLED
from django_ledger.io.io_generator import FAKER_IMPORTED

print(FAKER_INSTALLED, FAKER_IMPORTED)
"""


class DemoExtraUserMixIn:
    """
    Creates the user and entity the tests work with.
    """

    USERNAME: str = 'demo-extra-user'
    PASSWORD: str = 'NeverUseThisPassword13579'
    EMAIL: str = 'demo-extra-user@djangoledger.com'

    @classmethod
    def create_test_user(cls, superuser: bool = False):
        """
        Creates the test user, as a superuser when the test goes through the Django admin.
        """
        if superuser:
            return UserModel.objects.create_superuser(username=cls.USERNAME, password=cls.PASSWORD, email=cls.EMAIL)
        return UserModel.objects.create_user(username=cls.USERNAME, password=cls.PASSWORD, email=cls.EMAIL)

    @classmethod
    def create_test_entity(cls, admin) -> EntityModel:
        """
        Creates an empty entity administered by the given user.
        """
        return EntityModel.create_entity(
            name='Demo Extra Test Entity',
            use_accrual_method=True,
            fy_start_month=1,
            admin=admin,
        )


class CoreImportWithoutFakerTest(SimpleTestCase):
    """The package loads its URLs, views, forms, admin and generator module when Faker can't be imported."""

    def test_package_imports_and_reports_faker_as_missing(self):
        """A fresh Python process that can't import Faker still imports the package and sees Faker as missing."""
        environment = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'dev_env.settings'}
        completed = subprocess.run(
            [sys.executable, '-c', IMPORT_WITHOUT_FAKER_SCRIPT],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        self.assertEqual(completed.stdout.strip().splitlines()[-1], 'False False')


class GeneratorWithoutFakerTest(DemoExtraUserMixIn, TestCase):
    """The generator and populate_random_data() refuse to run without Faker and say how to install it."""

    @classmethod
    def setUpTestData(cls):
        cls.user_model = cls.create_test_user()
        cls.entity_model = cls.create_test_entity(admin=cls.user_model)

    def test_generator_raises_the_demo_extra_message(self):
        """Creating an EntityDataGenerator raises ImproperlyConfigured with the demo extra message."""
        with patch(GENERATOR_FAKER_FLAG, False):
            with self.assertRaisesMessage(ImproperlyConfigured, str(FAKER_MISSING_MESSAGE)):
                EntityDataGenerator(
                    user_model=self.user_model,
                    entity_model=self.entity_model,
                    start_dttm=get_localtime() - timedelta(days=30),
                    capital_contribution=Decimal('50000.00'),
                    days_forward=30,
                )

    def test_populate_random_data_raises_and_creates_nothing(self):
        """EntityModel.populate_random_data() raises the same message and leaves the entity without transactions."""
        with patch(GENERATOR_FAKER_FLAG, False):
            with self.assertRaisesMessage(ImproperlyConfigured, str(FAKER_MISSING_MESSAGE)):
                self.entity_model.populate_random_data(start_date=get_localtime() - timedelta(days=30))
        self.assertFalse(TransactionModel.objects.for_entity(entity_model=self.entity_model).exists())

    def test_message_names_the_demo_extra(self):
        """The message tells the user which extra to install."""
        self.assertIn(DEMO_EXTRA, str(FAKER_MISSING_MESSAGE))


class EntityCreateFormWithoutFakerTest(TestCase):
    """The entity create form turns the sample data option off without Faker and rejects it if posted anyway."""

    def test_sample_data_option_is_disabled_and_explained(self):
        """The sample data checkbox renders disabled, with help text naming the demo extra."""
        with patch(FORM_FAKER_FLAG, False):
            form = EntityModelCreateForm()
        sample_data_field = form.fields['generate_sample_data']
        self.assertTrue(sample_data_field.widget.attrs.get('disabled'))
        self.assertEqual(sample_data_field.help_text, FAKER_MISSING_MESSAGE)
        self.assertIn(DEMO_EXTRA, form.as_p())

    def test_posted_sample_data_is_rejected(self):
        """A submission that asks for sample data anyway is invalid and carries the demo extra message."""
        with patch(FORM_FAKER_FLAG, False):
            form = EntityModelCreateForm(data={**NEW_ENTITY_POST_DATA, 'generate_sample_data': 'on'})
            self.assertFalse(form.is_valid())
        self.assertIn(str(FAKER_MISSING_MESSAGE), form.non_field_errors())

    def test_sample_data_option_is_unchanged_with_faker(self):
        """With Faker installed the checkbox stays enabled and has no help text, as before."""
        with patch(FORM_FAKER_FLAG, True):
            form = EntityModelCreateForm()
        sample_data_field = form.fields['generate_sample_data']
        self.assertNotIn('disabled', sample_data_field.widget.attrs)
        self.assertEqual(sample_data_field.help_text, '')


class EntityCreateViewWithoutFakerTest(DemoExtraUserMixIn, TestCase):
    """The entity create page keeps working without Faker and never leaves a half-created entity."""

    @classmethod
    def setUpTestData(cls):
        cls.user_model = cls.create_test_user()

    def setUp(self):
        self.client.login(username=self.USERNAME, password=self.PASSWORD)
        self.create_url = reverse('django_ledger:entity-create')

    def test_create_page_loads_with_the_option_disabled(self):
        """GET returns 200 and shows the demo extra message next to the disabled option."""
        with patch(FORM_FAKER_FLAG, False):
            response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, DEMO_EXTRA)
        self.assertTrue(response.context['form'].fields['generate_sample_data'].widget.attrs.get('disabled'))

    def test_posted_sample_data_shows_an_error_and_creates_no_entity(self):
        """A POST asking for sample data re-renders the form with the message and saves no entity."""
        entity_count = EntityModel.objects.count()
        with patch(FORM_FAKER_FLAG, False):
            response = self.client.post(self.create_url, data={**NEW_ENTITY_POST_DATA, 'generate_sample_data': 'on'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, DEMO_EXTRA)
        self.assertEqual(EntityModel.objects.count(), entity_count)

    def test_entity_without_sample_data_is_still_created(self):
        """A POST without sample data creates the entity and its chart of accounts and redirects home."""
        with patch(FORM_FAKER_FLAG, False):
            response = self.client.post(self.create_url, data=NEW_ENTITY_POST_DATA)
        self.assertRedirects(response, reverse('django_ledger:home'), fetch_redirect_response=False)
        entity_model = EntityModel.objects.get(name=NEW_ENTITY_POST_DATA['name'])
        self.assertTrue(entity_model.has_default_coa())


class AdminPopulateRandomDataWithoutFakerTest(DemoExtraUserMixIn, TestCase):
    """The admin sample data action shows the demo extra message instead of failing."""

    @classmethod
    def setUpTestData(cls):
        cls.user_model = cls.create_test_user(superuser=True)
        cls.entity_model = cls.create_test_entity(admin=cls.user_model)

    def setUp(self):
        self.client.login(username=self.USERNAME, password=self.PASSWORD)

    def test_action_shows_the_message_and_creates_nothing(self):
        """Running the action redirects back to the list with an error message and adds no transactions."""
        changelist_url = reverse('admin:django_ledger_entitymodel_changelist')
        with patch(GENERATOR_FAKER_FLAG, False):
            response = self.client.post(
                changelist_url,
                data={'action': 'populate_random_data', '_selected_action': [str(self.entity_model.uuid)]},
                follow=True,
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(FAKER_MISSING_MESSAGE), [str(message) for message in response.context['messages']])
        self.assertFalse(TransactionModel.objects.for_entity(entity_model=self.entity_model).exists())
