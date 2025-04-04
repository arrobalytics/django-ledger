from django.test import override_settings
from django_ledger.tests.base import DjangoLedgerBaseTest

class FundFeatureTests(DjangoLedgerBaseTest):
    def test_fund_feature_enablement(self):
        from importlib import reload
        from django.conf import settings
        from django_ledger import settings as dl_settings

        # first test that the fund feature is disabled by default
        self.assertFalse(hasattr(settings, 'DJANGO_LEDGER_USE_FUNDS'))  # app's settings (i.e. dev_env in this case) doesn't override it
        self.assertTrue(hasattr(dl_settings, 'DJANGO_LEDGER_USE_FUNDS'))    # django_ledger settings file has it defined
        self.assertFalse(dl_settings.DJANGO_LEDGER_USE_FUNDS)               # and the default is False

        # now, override the settings file and reimport the django_ledger settings file
        with override_settings(DJANGO_LEDGER_USE_FUNDS=True):
            reload(dl_settings)
            self.assertTrue(hasattr(settings, 'DJANGO_LEDGER_USE_FUNDS'))   # app's settings now has the override setting
            self.assertTrue(hasattr(dl_settings, 'DJANGO_LEDGER_USE_FUNDS'))    # django_ledger settings file is defined
            self.assertTrue(dl_settings.DJANGO_LEDGER_USE_FUNDS)                # and it's overridden to True


@override_settings(DJANGO_LEDGER_USE_FUNDS=True)
class FundModelTests(DjangoLedgerBaseTest):
    pass
