import re

from django.template.loader import get_template
from django.urls import reverse

from django_ledger.tests.base import DjangoLedgerBaseTest

TFOOT_HEADER_WITHOUT_SCOPE = re.compile(r'<tfoot>(?:(?!</tfoot>).)*?<th(?![^>]*\bscope=)[\s>]', re.DOTALL)


class TemplateAccessibilityTests(DjangoLedgerBaseTest):
    def setUp(self):
        self.login_client()
        self.entity_model = self.ENTITY_MODEL_QUERYSET.first()

    def get(self, url):
        response = self.CLIENT.get(url)
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_bill_detail_declares_language_and_footer_row_header(self):
        bill_model = self.entity_model.get_bills().first()
        html = self.get(
            reverse(
                'django_ledger:bill-detail',
                kwargs={
                    'entity_slug': self.entity_model.slug,
                    'bill_pk': bill_model.uuid,
                },
            )
        )
        self.assertRegex(html, r'<html lang="[a-z]{2}')
        self.assertIn('<th scope="row">', html)
        self.assertIsNone(TFOOT_HEADER_WITHOUT_SCOPE.search(html))

    def test_edited_templates_compile(self):
        for name in (
            'bills/tags/bill_item_formset.html',
            'estimate/tags/ce_item_formset.html',
            'inventory/tags/inventory_table.html',
            'invoice/invoice_detail.html',
            'invoice/tags/invoice_item_formset.html',
            'purchase_order/includes/po_item_formset.html',
            'purchase_order/po_update.html',
            'data_import/includes/staged_txs_form_card.html',
        ):
            with self.subTest(name=name):
                get_template(f'django_ledger/{name}')

    def test_list_search_inputs_have_accessible_names(self):
        ledger_html = self.get(reverse('django_ledger:ledger-list', kwargs={'entity_slug': self.entity_model.slug}))
        self.assertIn('aria-label="Search ledgers"', ledger_html)
        account_html = self.get(
            reverse(
                'django_ledger:account-list',
                kwargs={
                    'entity_slug': self.entity_model.slug,
                    'coa_slug': self.entity_model.default_coa.slug,
                },
            )
        )
        self.assertIn('aria-label="Search accounts by code or name"', account_html)
