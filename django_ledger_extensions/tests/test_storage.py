from django.core.files.storage import FileSystemStorage
from django.test import TestCase, override_settings

from django_ledger_extensions.storage import (
    beleg_storage_enabled,
    clear_beleg_storage_cache,
    get_beleg_storage,
)


class BelegStorageTests(TestCase):

    def setUp(self):
        clear_beleg_storage_cache()

    def tearDown(self):
        clear_beleg_storage_cache()

    def test_local_storage_by_default(self):
        self.assertFalse(beleg_storage_enabled())
        storage = get_beleg_storage()
        self.assertIsInstance(storage, FileSystemStorage)

    @override_settings(
        DJANGO_LEDGER_AWS_STORAGE_BUCKET_NAME='my-school-belege',
        DJANGO_LEDGER_AWS_S3_REGION_NAME='eu-central-1',
    )
    def test_s3_storage_when_bucket_set(self):
        try:
            import storages  # noqa: F401
        except ImportError:
            self.skipTest('django-storages not installed')

        self.assertTrue(beleg_storage_enabled())
        storage = get_beleg_storage()
        self.assertIn('storages.backends.s3', storage.__class__.__module__)
        self.assertEqual(storage.bucket_name, 'my-school-belege')
        self.assertEqual(storage.region_name, 'eu-central-1')
        self.assertEqual(storage.location, 'belege')
