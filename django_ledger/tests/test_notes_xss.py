from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from django.contrib.messages.storage.base import Message
from django.contrib.messages.storage.cookie import MessageDecoder, MessageEncoder
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import SafeData

from django_ledger.models import BillModel, InvoiceModel, VendorModel
from django_ledger.tests.base import DjangoLedgerBaseTest

SAFE_SCHEMES = {'', 'http', 'https', 'mailto'}
ALLOWED_ATTRIBUTES = {'href', 'src', 'alt', 'title'}
TEMPLATE_HANDLER = r"^djLedger\.toggleModal\('[\w-]+'\)$"


class _Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def elements(html):
    parser = _Elements()
    parser.feed(html)
    return parser.elements


def notes_html(text):
    return BillModel(markdown_notes=text).notes_html()


HOSTILE_NOTES = (
    '<script>alert(1)</script>',
    'hi <img src=x onerror=alert(1)>',
    '<a href="javascript:alert(1)">x</a>',
    '<div onclick="alert(1)">block</div>',
    '<svg onload=alert(1)>',
    '[x](javascript:alert(1))',
    '[x]( JaVaScRiPt:alert(1))',
    '[x](java\tscript:alert(1))',
    '[x](java&#10;script:alert(1))',
    '[x](&#106;avascript:alert(1))',
    '[x](javascript&colon;alert(1))',
    '[x](data:text/html;base64,PHNjcmlwdD4=)',
    '[x](vbscript:msgbox(1))',
    '![i](javascript:alert(1))',
    '[x](https://example.com/"onmouseover="alert(1))',
    '[x]: javascript:alert(1)\n\n[ref][x]',
    '<https://example.com/"><script>alert(1)</script>',
)


class NotesHtmlTests(SimpleTestCase):
    def test_hostile_notes_render_no_markup_or_unsafe_urls(self):
        for text in HOSTILE_NOTES:
            with self.subTest(text=text):
                html = notes_html(text)
                for tag, attrs in elements(html):
                    self.assertIn(tag, {'p', 'a', 'img', 'code', 'pre', 'em', 'strong'})
                    self.assertLessEqual(set(attrs), ALLOWED_ATTRIBUTES)
                    for name in ('href', 'src'):
                        if name in attrs:
                            self.assertIn(urlsplit(attrs[name]).scheme.lower(), SAFE_SCHEMES)

    def test_markdown_formatting_and_safe_links_are_kept(self):
        html = notes_html(
            '# Heading\n\n> quote\n\n- a\n- b\n\n**bold** `1 < 2`\n\n'
            '[site](https://example.com) [rel](/bills/) [mail](mailto:a@b.c) [anchor](#top) ![logo](/static/logo.png)'
        )
        tags = [tag for tag, _ in elements(html)]
        for tag in ('h1', 'blockquote', 'ul', 'li', 'strong', 'code', 'a', 'img'):
            self.assertIn(tag, tags)
        hrefs = [attrs.get('href') for tag, attrs in elements(html) if tag == 'a']
        self.assertEqual(hrefs, ['https://example.com', '/bills/', 'mailto:a@b.c', '#top'])
        self.assertIn('1 &lt; 2', html)

    def test_entities_autolinks_and_attribute_quoting_are_unchanged(self):
        self.assertEqual(notes_html('&copy; &amp; &#60;script&#62;'), '<p>&copy; &amp; &#60;script&#62;</p>')
        self.assertIn('href="&#109;&#97;&#105;&#108;&#116;&#111;&#58;', notes_html('<a@b.c>'))
        self.assertEqual(
            [attrs.get('href') for tag, attrs in elements(notes_html('<a@b.c>')) if tag == 'a'], ['mailto:a@b.c']
        )
        self.assertEqual(notes_html('<https://x.y>'), '<p><a href="https://x.y">https://x.y</a></p>')
        self.assertEqual(
            notes_html('![alt "q" <x>][r]\n\n[r]: javascript:alert(1) "t"'),
            '<p><img alt="alt &quot;q&quot; &lt;x&gt;" title="t" /></p>',
        )
        self.assertEqual(
            notes_html('![a" onerror="alert(1)](https://e.com/i.png)'),
            '<p><img alt="a&quot; onerror=&quot;alert(1)" src="https://e.com/i.png" /></p>',
        )

    def test_raw_html_is_shown_as_text(self):
        self.assertEqual(notes_html('<b>b</b>'), '<p>&lt;b&gt;b&lt;/b&gt;</p>')

    def test_result_is_marked_safe_and_empty_notes_are_blank(self):
        self.assertIsInstance(notes_html('text'), SafeData)
        self.assertEqual(notes_html(''), '')
        self.assertEqual(BillModel(markdown_notes=None).notes_html(), '')


class SafeRenderingTemplateTests(SimpleTestCase):
    def test_card_escapes_plain_strings_and_renders_rendered_notes(self):
        card = 'django_ledger/includes/card_markdown.html'
        plain = render_to_string(card, {'style': 'card_1', 'notes_html': '<script>alert(1)</script>'})
        self.assertNotIn('<script>', plain)
        self.assertIn('&lt;script&gt;', plain)
        rendered = render_to_string(card, {'style': 'card_1', 'notes_html': notes_html('**bold**')})
        self.assertIn('<strong>bold</strong>', rendered)
        empty = render_to_string(card, {'style': 'card_1', 'notes_html': ''})
        self.assertIn('No available notes to display...', empty)

    def test_messages_escape_text_and_keep_built_links(self):
        link = format_html('Update <a href="{}">here</a> for {}.', '/bills/1/update/', '<b>Bill</b>')
        html = render_to_string(
            'django_ledger/includes/messages.html',
            {
                'messages': [Message(30, 'Imported <img src=x onerror=alert(1)> "q"'), Message(30, link)],
            },
        )
        self.assertNotIn('<img', html)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)
        self.assertIn('<a href="/bills/1/update/">here</a>', html)
        self.assertIn('&lt;b&gt;Bill&lt;/b&gt;', html)

    def test_message_storage_preserves_safe_data_classification(self):
        safe = format_html('<a href="{}">here</a>', '/x/')
        encoded = MessageEncoder().encode([Message(30, safe), Message(30, '<b>plain</b>')])
        decoded = MessageDecoder().decode(encoded)
        self.assertIsInstance(decoded[0].message, SafeData)
        self.assertNotIsInstance(decoded[1].message, SafeData)


class DetailPageXssTests(DjangoLedgerBaseTest):
    def setUp(self):
        self.login_client()
        self.entity_model = self.ENTITY_MODEL_QUERYSET.first()

    def detail(self, viewname, **kwargs):
        response = self.CLIENT.get(reverse(viewname, kwargs={'entity_slug': self.entity_model.slug, **kwargs}))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def assert_no_injected_markup(self, html):
        for tag, attrs in elements(html):
            self.assertFalse(tag == 'img' and attrs.get('src') == 'x', attrs)
            handlers = {name: value for name, value in attrs.items() if name.startswith('on')}
            for name, value in handlers.items():
                self.assertEqual(name, 'onclick', attrs)
                self.assertRegex(value, TEMPLATE_HANDLER, attrs)
            for name in ('href', 'src'):
                self.assertNotIn('javascript:alert(7)', (attrs.get(name) or '').lower())

    def subtitles(self, html):
        return [
            parse_qs(urlsplit(attrs['href']).query)
            for tag, attrs in elements(html)
            if tag == 'a' and 'report_subtitle=' in (attrs.get('href') or '')
        ]

    def test_bill_detail_escapes_notes_and_encodes_vendor_in_report_links(self):
        bill_model = next(bill for bill in self.entity_model.get_bills() if bill.is_active())
        hostile_name = 'Evil" onmouseover="alert(7)&other=1#frag'
        VendorModel.objects.filter(uuid=bill_model.vendor_id).update(vendor_name=hostile_name)
        BillModel.objects.filter(uuid=bill_model.uuid).update(
            markdown_notes='<img src=x onerror=alert(7)> [x](javascript:alert(7))'
        )
        html = self.detail('django_ledger:bill-detail', bill_pk=bill_model.uuid)
        self.assert_no_injected_markup(html)
        bill_model.refresh_from_db()
        queries = self.subtitles(html)
        self.assertEqual(len(queries), 3)
        for query in queries:
            self.assertEqual(query['report_subtitle'], [bill_model.generate_descriptive_title()])
            self.assertNotIn('other', query)

    def test_invoice_detail_encodes_customer_in_report_links(self):
        invoice_model = next(invoice for invoice in self.entity_model.get_invoices() if invoice.is_active())
        invoice_model.customer.__class__.objects.filter(uuid=invoice_model.customer_id).update(
            customer_name='Acme & Co #1 /x'
        )
        html = self.detail('django_ledger:invoice-detail', invoice_pk=invoice_model.uuid)
        invoice_model.refresh_from_db()
        queries = self.subtitles(html)
        self.assertEqual(len(queries), 3)
        for query in queries:
            self.assertEqual(query['report_subtitle'], [invoice_model.generate_descriptive_title()])

    def test_unconfigured_bill_warning_renders_link_and_escapes_number(self):
        bill_model = self.entity_model.get_bills().first()
        BillModel.objects.filter(uuid=bill_model.uuid).update(cash_account=None, bill_number='<b>B-1</b>')
        html = self.detail('django_ledger:bill-detail', bill_pk=bill_model.uuid)
        update_url = reverse(
            'django_ledger:bill-update',
            kwargs={
                'entity_slug': self.entity_model.slug,
                'bill_pk': bill_model.uuid,
            },
        )
        self.assertIn(f'<a href="{update_url}">here</a>', html)
        self.assertIn('Bill &lt;b&gt;B-1&lt;/b&gt; has not been fully set up.', html)


class InvoiceNotesTests(SimpleTestCase):
    def test_invoice_notes_use_the_same_renderer(self):
        self.assertEqual(InvoiceModel(markdown_notes='<b>x</b>').notes_html(), '<p>&lt;b&gt;x&lt;/b&gt;</p>')
