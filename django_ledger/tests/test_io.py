from datetime import timedelta, datetime
from random import randint
from zoneinfo import ZoneInfo

from django.conf import settings

from django_ledger.io.io_core import IOValidationError
from django_ledger.models import EntityModel
from django_ledger.tests.base import DjangoLedgerBaseTest


class IOTest(DjangoLedgerBaseTest):

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
