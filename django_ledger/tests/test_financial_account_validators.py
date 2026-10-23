import re
from time import perf_counter

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, int_list_validator
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TestCase

from django_ledger.forms.bank_account import BankAccountCreateForm
from django_ledger.models import BankAccountModel, EntityModel, VendorModel

DIGIT_MODELS = (BankAccountModel, VendorModel)
DIGIT_FIELDS = ('account_number', 'routing_number')
VALID_DIGITS = ('0', '000012', '012345678901234567890123456789', '١٢٣', '１２３', '1٢３')
INVALID_DIGITS = ('²', 'Ⅲ', '+12', '-12', '1,2', '1|2', '1 2', ' ', '1\n', '\n1', '12.3', '12a')


def digit_validator(field):
    [validator] = [v for v in field.validators if isinstance(v, RegexValidator)]
    return validator


class FinancialAccountDigitFieldTests(SimpleTestCase):
    def clean(self, model, field, value):
        return model._meta.get_field(field).clean(value, model())

    def test_validator_pattern_has_no_nested_repetition(self):
        for model in DIGIT_MODELS:
            for field in DIGIT_FIELDS:
                with self.subTest(model=model.__name__, field=field):
                    validator = digit_validator(model._meta.get_field(field))
                    self.assertEqual(validator.regex.pattern, r'^\d+\Z')
                    self.assertEqual(validator.regex.flags, re.UNICODE)

    def test_models_package_still_exports_int_list_validator(self):
        from django_ledger import models

        self.assertIs(models.int_list_validator, int_list_validator)

    def test_digit_strings_are_accepted_unchanged(self):
        for model in DIGIT_MODELS:
            for field in DIGIT_FIELDS:
                for value in VALID_DIGITS + ('', None):
                    with self.subTest(model=model.__name__, field=field, value=value):
                        self.assertEqual(self.clean(model, field, value), value)

    def test_non_digit_strings_keep_the_error_contract(self):
        for model in DIGIT_MODELS:
            for field in DIGIT_FIELDS:
                for value in INVALID_DIGITS:
                    with self.subTest(model=model.__name__, field=field, value=value):
                        with self.assertRaises(ValidationError) as raised:
                            self.clean(model, field, value)
                        [error] = raised.exception.error_list
                        self.assertEqual(error.message, 'Only digits allowed')
                        self.assertEqual(error.code, 'invalid')
                        self.assertEqual(error.params, {'value': value})

    def test_max_length_is_unchanged(self):
        for model in DIGIT_MODELS:
            for field in DIGIT_FIELDS:
                with self.subTest(model=model.__name__, field=field):
                    with self.assertRaises(ValidationError) as raised:
                        self.clean(model, field, '1' * 31)
                    self.assertEqual([e.code for e in raised.exception.error_list], ['max_length'])

    def test_clean_fields_reports_only_the_digit_fields(self):
        for model in DIGIT_MODELS:
            with self.subTest(model=model.__name__):
                instance = model(account_number='12X', routing_number='0034')
                others = [f.name for f in model._meta.fields if f.name not in DIGIT_FIELDS]
                with self.assertRaises(ValidationError) as raised:
                    instance.clean_fields(exclude=others)
                self.assertEqual(list(raised.exception.error_dict), ['account_number'])
                model(account_number='0012', routing_number='٠٣٤').clean_fields(exclude=others)

    def test_near_miss_input_is_rejected_in_linear_time(self):
        # The previous nested pattern took about two seconds on this input and doubled per digit.
        for model in DIGIT_MODELS:
            for field in DIGIT_FIELDS:
                for value in ('1' * 26 + 'X', '1' * 26 + '²'):
                    with self.subTest(model=model.__name__, field=field, value=value):
                        started = perf_counter()
                        with self.assertRaises(ValidationError):
                            self.clean(model, field, value)
                        self.assertLess(perf_counter() - started, 0.5)


class FinancialAccountMigrationStateTests(SimpleTestCase):
    def test_initial_migration_validators_have_no_nested_repetition(self):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        state = loader.project_state(('django_ledger', '0001_initial'))
        for model in DIGIT_MODELS:
            historical = state.models['django_ledger', model._meta.model_name]
            for field in DIGIT_FIELDS:
                with self.subTest(model=model.__name__, field=field):
                    self.assertEqual(digit_validator(historical.fields[field]).regex.pattern, r'^\d+\Z')

    def test_migration_state_matches_runtime_validators(self):
        state = MigrationLoader(None, ignore_no_migrations=True).project_state()
        for model in DIGIT_MODELS:
            historical = state.models['django_ledger', model._meta.model_name]
            for field in DIGIT_FIELDS:
                with self.subTest(model=model.__name__, field=field):
                    self.assertEqual(
                        digit_validator(historical.fields[field]),
                        digit_validator(model._meta.get_field(field)),
                    )


class BankAccountCreateFormDigitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='digits-owner')
        cls.entity = EntityModel.create_entity('Digits Entity', False, cls.user, 1)
        cls.entity.populate_default_coa(activate_accounts=True)
        cls.cash_account = cls.entity.get_default_coa_accounts().filter(role='asset_ca_cash').first()

    def form(self, **overrides):
        data = {
            'name': 'Operating',
            'account_type': BankAccountModel.ACCOUNT_CHECKING,
            'account_number': '000123',
            'routing_number': '0456',
            'account_model': self.cash_account.uuid,
            'active': True,
            **overrides,
        }
        return BankAccountCreateForm(data=data, entity_slug=self.entity.slug, user_model=self.user)

    def test_digits_are_kept_with_leading_zeroes_and_unicode_digits(self):
        for account_number, routing_number in (('000123', '0456'), ('١٢٣', '１２３'), (' 0789\n', '\t0012 ')):
            with self.subTest(account_number=account_number, routing_number=routing_number):
                form = self.form(account_number=account_number, routing_number=routing_number)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.instance.account_number, account_number.strip())
                self.assertEqual(form.instance.routing_number, routing_number.strip())

    def test_blank_inputs_become_null(self):
        for blank in ('', ' \t\n '):
            with self.subTest(blank=blank):
                form = self.form(account_number=blank, routing_number=blank)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertIsNone(form.instance.account_number)
                self.assertIsNone(form.instance.routing_number)

    def test_duplicate_check_still_applies(self):
        self.assertTrue(self.form().is_valid())
        bank_account = self.form().save(commit=False)
        bank_account.entity_model = self.entity
        bank_account.save()
        form = self.form()
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ['Duplicate bank account model.'])

    def test_non_digit_inputs_are_rejected_per_field(self):
        cases = (
            ('12-34', '12-34'),
            ('1²', '1²'),
            (' 12X ', '12X'),
            ('1' * 29 + 'X', '1' * 29 + 'X'),
            ('1' * 29 + '²', '1' * 29 + '²'),
        )
        for field in DIGIT_FIELDS:
            for value, cleaned in cases:
                with self.subTest(field=field, value=value):
                    started = perf_counter()
                    form = self.form(**{field: value})
                    self.assertFalse(form.is_valid())
                    self.assertLess(perf_counter() - started, 3.0)
                    self.assertEqual(list(form.errors), [field])
                    [error] = form.errors.as_data()[field]
                    self.assertEqual(
                        (error.message, error.code, error.params),
                        ('Only digits allowed', 'invalid', {'value': cleaned}),
                    )
