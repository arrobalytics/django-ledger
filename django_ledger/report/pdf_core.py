from typing import Optional, Dict

from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError

from django_ledger.io import IODigest
from django_ledger.settings import DJANGO_LEDGER_PDF_SUPPORT_ENABLED
from django_ledger.templatetags.django_ledger import currency_symbol, currency_format


def load_support():
    support = list()
    if DJANGO_LEDGER_PDF_SUPPORT_ENABLED:
        from fpdf import FPDF
        support.append(FPDF)
    return support


class PDFReportValidationError(ValidationError):
    pass


class BasePDFSupport(*load_support()):
    FOOTER_LOGO_PATH = 'django_ledger/logo/django-ledger-logo-report.png'

    def __init__(self,
                 *args,
                 io_digest: IODigest,
                 **kwargs):

        if not DJANGO_LEDGER_PDF_SUPPORT_ENABLED:
            raise NotImplementedError('PDF support not enabled.')

        super().__init__(*args, **kwargs)
        self.FONT_SIZE: int = 9
        self.FONT_FAMILY: str = 'Arial'
        self.IO_DIGEST: IODigest = io_digest
        self.CURRENCY_SYMBOL = currency_symbol()
        self.set_font(family=self.FONT_FAMILY, size=self.FONT_SIZE)
        self.alias_nb_pages()
        self.add_page()
        self.TABLE_HEADERS: Optional[Dict]

    def header(self):
        self.set_font(
            family=self.FONT_FAMILY,
            style='B',
            size=self.FONT_SIZE)

        # Report Type
        self.set_font(
            family='Arial',
            size=self.FONT_SIZE + 2
        )
        w = self.get_string_width(self.get_report_type())
        self.set_x((210 - w) / 2)
        self.cell(w, 3, self.get_report_type(), ln=1)

        # Report Title
        self.set_font(
            family=self.FONT_FAMILY,
            size=self.FONT_SIZE + 6,
            style='B'
        )
        entity_title = self.get_entity_title()
        w = self.get_string_width(entity_title)
        self.set_x((210 - w) / 2)
        self.cell(w=w,
                  h=6,
                  txt=entity_title,
                  border=0,
                  ln=1,
                  align='C')

        # Period
        self.set_font(
            family=self.FONT_FAMILY,
            size=self.FONT_SIZE - 1,
            style='I'
        )
        from_date = self.IO_DIGEST.get_from_date().strftime('%m-%d-%Y')
        to_date = self.IO_DIGEST.get_to_date().strftime('%m-%d-%Y')
        if from_date and to_date:
            period = f'From {from_date} through {to_date}'
        elif to_date:
            period = f'Through {to_date}'
        else:
            raise PDFReportValidationError('PDF report must have dates specified.')
        w = self.get_string_width(period)
        self.set_x((210 - w) / 2)
        self.cell(w=w,
                  h=5,
                  txt=period,
                  align='C')

        # Line break
        self.ln(10)

    def print_headers(self):
        for k, header in self.TABLE_HEADERS.items():
            self.set_font(self.FONT_FAMILY, header.get('style', ''), self.FONT_SIZE)
            w = self.get_string_width(header['title']) + header['spacing']
            self.cell(
                w=w,
                h=5,
                txt=header['title'],
                align=header.get('align'),
            )
        self.ln(8)

    def print_section_title(self, title):
        self.set_font(self.FONT_FAMILY, 'BU', self.FONT_SIZE + 4)

        # Assets title...
        self.cell(
            w=20,
            h=10,
            txt=title,
            ln=1

        )

    def get_entity_title(self):
        if self.IO_DIGEST.is_entity_model():
            return self.IO_DIGEST.IO_MODEL.name

    def get_report_type(self):
        return self.REPORT_TYPE

    def get_report_footer_logo_path(self) -> str:
        return finders.find(self.FOOTER_LOGO_PATH)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-25)
        # Arial italic 8
        self.set_font(self.FONT_FAMILY, 'I', 8)
        # Page number
        self.cell(0, 5, 'Page ' + str(self.page_no()) + '/{nb}', 0, 1, 'C')
        self.set_font(family=self.FONT_FAMILY, size=self.FONT_SIZE - 3)
        self.cell(0, 5, 'Powered by:', 0, 1, 'C')
        self.image(self.get_report_footer_logo_path(), w=30, x=(200 - 30) / 2, link='https://www.djangoledger.com')

    def create_pdf_report(self):
        raise NotImplementedError()
