"""
Data import (OFX) view integration tests.
"""

from __future__ import annotations

from django_ledger.tests.test_views.base import DjangoLedgerViewTestCase


class DataImportViewTests(DjangoLedgerViewTestCase):
    def test_import_job_list_login_required(self):
        url = self.reverse_entity('import-job-list')
        self.assert_login_required(url)

    def test_import_job_list_unauthorized_403(self):
        url = self.reverse_foreign('import-job-list')
        self.assert_unauthorized_entity(url)

    def test_import_job_list_200_empty_ok(self):
        url = self.reverse_entity('import-job-list')
        self.assert_get_ok(url)

    def test_data_import_ofx_login_required(self):
        url = self.reverse_entity('data-import-ofx')
        self.assert_login_required(url)

    def test_data_import_ofx_unauthorized_403(self):
        url = self.reverse_foreign('data-import-ofx')
        self.assert_unauthorized_entity(url)

    def test_data_import_ofx_get_200(self):
        url = self.reverse_entity('data-import-ofx')
        self.assert_get_ok(url)
