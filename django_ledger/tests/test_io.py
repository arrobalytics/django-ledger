from datetime import timedelta, datetime
from decimal import Decimal
from random import randint
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from django_ledger.io.io_core import IOValidationError, validate_io_timestamp
from django_ledger.models import EntityModel
from django_ledger.tests.base import DjangoLedgerBaseTest


@override_settings(TIME_ZONE='America/New_York')
class IOTimestampTest(SimpleTestCase):

    @override_settings(USE_TZ=True)
    def test_datetime_strings_preserve_time_and_offset(self):
        for timestamp in (
            '2024-07-01T14:35:27.123456Z',
            '2024-07-01T00:35:27.123456+10:00',
            '2024-07-01T23:35:27.123456-05:00',
        ):
            with self.subTest(timestamp=timestamp):
                expected = datetime.fromisoformat(timestamp)
                actual = validate_io_timestamp(timestamp)
                self.assertEqual(actual, expected)
                self.assertEqual(actual.utcoffset(), expected.utcoffset())

    def test_naive_datetime_strings_preserve_time(self):
        timestamp = '2024-07-01T14:35:27.123456'
        for use_tz in (True, False):
            with self.subTest(use_tz=use_tz), self.settings(USE_TZ=use_tz):
                expected = datetime.fromisoformat(timestamp)
                if use_tz:
                    expected = expected.replace(tzinfo=ZoneInfo(settings.TIME_ZONE))
                self.assertEqual(validate_io_timestamp(timestamp), expected)

    @override_settings(USE_TZ=False)
    def test_offset_strings_become_local_naive_without_use_tz(self):
        # 00:35 at +10:00 is 10:35 the previous day in New York (UTC-04:00).
        self.assertEqual(
            validate_io_timestamp('2024-07-01T00:35:27.123456+10:00'),
            datetime(2024, 6, 30, 10, 35, 27, 123456),
        )

    def test_date_strings_still_use_local_midnight(self):
        for use_tz in (True, False):
            with self.subTest(use_tz=use_tz), self.settings(USE_TZ=use_tz):
                expected = datetime(2024, 7, 1)
                if use_tz:
                    expected = expected.replace(tzinfo=ZoneInfo(settings.TIME_ZONE))
                self.assertEqual(validate_io_timestamp('2024-07-01'), expected)


class IOTest(DjangoLedgerBaseTest):

    def test_commit_txs_preserves_datetime_string(self):
        entity_model = self.get_random_entity_model()
        ledger_model = entity_model.create_ledger(name='Timestamp regression')
        timestamp = '2024-07-01T00:35:27.123456+10:00'
        transactions = [
            {
                'account': self.get_random_account(entity_model, balance_type=tx_type),
                'amount': Decimal('10.00'),
                'tx_type': tx_type,
                'description': 'Timestamp regression',
            }
            for tx_type in ('debit', 'credit')
        ]

        journal_entry, _ = ledger_model.commit_txs(
            je_timestamp=timestamp,
            je_txs=transactions,
        )
        journal_entry.refresh_from_db()
        self.assertEqual(journal_entry.timestamp, datetime.fromisoformat(timestamp))

    def test_digest_dttm__dttm(self):
        self.assertTrue(settings.USE_TZ, msg='Timezone not enabled.')

        entity_model = self.get_random_entity_model()
        from_datetime = self.START_DATE
        to_datetime = self.START_DATE + timedelta(days=randint(10, 60))

        io_digest = entity_model.digest(from_date=from_datetime, to_date=to_datetime)
        self.assertTrue(isinstance(io_digest.get_to_datetime(), datetime))
        self.assertTrue(isinstance(io_digest.get_from_datetime(), datetime))
        self.assertEqual(io_digest.get_from_datetime(), from_datetime)
        self.assertEqual(io_digest.get_to_datetime(), to_datetime)

    def test_digest_dt__dttm(self):
        self.assertTrue(settings.USE_TZ, msg='Timezone not enabled.')

        entity_model = self.get_random_entity_model()
        from_datetime = self.START_DATE
        to_datetime = self.START_DATE + timedelta(days=randint(10, 60))

        io_digest = entity_model.digest(from_date=from_datetime.date(), to_date=to_datetime)
        self.assertTrue(isinstance(io_digest.get_to_datetime(), datetime))
        self.assertTrue(isinstance(io_digest.get_from_datetime(), datetime))

        self.assertEqual(
            # the assumed datetime given a date...
            io_digest.get_from_datetime(),

            # equals the localized datetime @ 0:00
            datetime.combine(
                from_datetime.date(),
                datetime.min.time(),
                tzinfo=ZoneInfo(settings.TIME_ZONE)
            )
        )

        self.assertEqual(io_digest.get_to_datetime(), to_datetime)

    def test_digest_dttm__dt(self):
        self.assertTrue(settings.USE_TZ, msg='Timezone not enabled.')

        entity_model = self.get_random_entity_model()
        from_datetime = self.START_DATE
        to_datetime = self.START_DATE + timedelta(days=randint(10, 60))

        io_digest = entity_model.digest(from_date=from_datetime, to_date=to_datetime.date())

        self.assertTrue(isinstance(io_digest.get_to_datetime(), datetime))
        self.assertTrue(isinstance(io_digest.get_from_datetime(), datetime))

        self.assertEqual(io_digest.get_from_datetime(), from_datetime)

        self.assertEqual(
            # the assumed datetime given a date...
            io_digest.get_to_datetime(),

            # equals the localized datetime @ 0:00
            datetime.combine(
                to_datetime.date(),
                datetime.min.time(),
                tzinfo=ZoneInfo(settings.TIME_ZONE)
            )
        )

    def test_digest_dt__dt(self):
        self.assertTrue(settings.USE_TZ, msg='Timezone not enabled.')

        entity_model = self.get_random_entity_model()
        from_datetime = self.START_DATE
        to_datetime = self.START_DATE + timedelta(days=randint(10, 60))

        io_digest = entity_model.digest(from_date=from_datetime.date(), to_date=to_datetime.date())

        self.assertTrue(isinstance(io_digest.get_to_datetime(), datetime))
        self.assertTrue(isinstance(io_digest.get_from_datetime(), datetime))

        self.assertEqual(
            # the assumed datetime given a date...
            io_digest.get_from_datetime(),

            # equals the localized datetime @ 0:00
            datetime.combine(
                from_datetime.date(),
                datetime.min.time(),
                tzinfo=ZoneInfo(settings.TIME_ZONE)
            )
        )

        self.assertEqual(
            # the assumed datetime given a date...
            io_digest.get_to_datetime(),

            # equals the localized datetime @ 0:00
            datetime.combine(
                to_datetime.date(),
                datetime.min.time(),
                tzinfo=ZoneInfo(settings.TIME_ZONE)
            )
        )

    def test_digest_none__dttm(self):
        self.assertTrue(settings.USE_TZ, msg='Timezone not enabled.')

        entity_model = self.get_random_entity_model()
        to_datetime = self.START_DATE + timedelta(days=randint(10, 60))

        io_digest = entity_model.digest(to_date=to_datetime)

        self.assertTrue(io_digest.get_from_datetime() is None)
        self.assertTrue(isinstance(io_digest.get_to_datetime(), datetime))

        self.assertEqual(
            # the assumed datetime given a date...
            io_digest.get_from_datetime(),

            # equals the localized datetime @ 0:00
            None
        )

        self.assertEqual(io_digest.get_to_datetime(), to_datetime)

    def test_digest_none__dt(self):
        self.assertTrue(settings.USE_TZ, msg='Timezone not enabled.')

        entity_model = self.get_random_entity_model()
        to_datetime = self.START_DATE + timedelta(days=randint(10, 60))

        io_digest = entity_model.digest(to_date=to_datetime.date())

        self.assertTrue(io_digest.get_from_datetime() is None)
        self.assertTrue(isinstance(io_digest.get_to_datetime(), datetime))

        self.assertEqual(
            # the assumed datetime given a date...
            io_digest.get_from_datetime(),

            # equals the localized datetime @ 0:00
            None
        )

        self.assertEqual(
            # the assumed datetime given a date...
            io_digest.get_to_datetime(),

            # equals the localized datetime @ 0:00
            datetime.combine(
                to_datetime.date(),
                datetime.min.time(),
                tzinfo=ZoneInfo(settings.TIME_ZONE)
            )
        )

    def test_digest_entity(self):
        entity_model = self.get_random_entity_model()
        from_datetime = self.START_DATE
        to_datetime = self.START_DATE + timedelta(days=randint(10, 60))

        with self.assertRaises(IOValidationError):
            entity_model.digest(
                entity_slug='1234',
                from_date=from_datetime,
                to_date=to_datetime
            )

        io_digest = entity_model.digest(
            entity_slug=entity_model.slug,
            from_date=from_datetime,
            to_date=to_datetime
        )

        self.assertTrue(isinstance(io_digest.IO_MODEL, EntityModel))
        self.assertTrue(io_digest.get_io_data(), io_digest.IO_DATA)
        self.assertTrue(io_digest.IO_DATA['entity_slug'], entity_model.slug)
        self.assertFalse(io_digest.IO_DATA['by_activity'])
        self.assertFalse(io_digest.IO_DATA['by_unit'])
        self.assertFalse(io_digest.IO_DATA['by_tx_type'])

        # io_digest = entity_model.digest(
        #     unit_slug='3212',
        #     from_date=from_datetime,
        #     to_date=to_datetime
        # )
        #
        # self.assertEqual(io_digest.get_io_txs_queryset().count(), 0)

    def test_io_transactions_belong_to_entity(self):
        entity_model = self.get_random_entity_model()
        from_datetime = self.START_DATE
        to_datetime = self.START_DATE + timedelta(days=randint(10, 60))

        io_digest = entity_model.digest(
            entity_slug=entity_model.slug,
            from_date=from_datetime,
            to_date=to_datetime,
            for_test=True
        )

        tx_qs = io_digest.get_io_txs_queryset()
        # Every transaction returned by the IO for an entity digest must belong to that entity.
        for tx in tx_qs:
            self.assertEqual(tx['journal_entry__ledger__entity_id'], entity_model.uuid)
