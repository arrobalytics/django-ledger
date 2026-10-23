from datetime import date

from django.test import SimpleTestCase

from django_ledger.io.io_core import IOResult


class IOResultTests(SimpleTestCase):
    def test_txs_queryset_is_keyword_only_and_excluded_from_repr_and_equality(self):
        result = IOResult(date(2026, 1, 1), date(2026, 12, 31), txs_queryset=['tx'])
        self.assertEqual(result.txs_queryset, ['tx'])
        self.assertIsNone(IOResult().txs_queryset)
        self.assertEqual(result, IOResult(date(2026, 1, 1), date(2026, 12, 31)))
        self.assertNotIn('txs_queryset', repr(result))
        with self.assertRaises(TypeError):
            IOResult(None, None, False, None, None, None, ['tx'])
