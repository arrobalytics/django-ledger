from typing import Optional, Dict

from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError

from django_ledger.io.io_digest import IODigestContextManager
from django_ledger.models.ledger import LedgerModel
from django_ledger.models.unit import EntityUnitModel
from django_ledger.settings import DJANGO_LEDGER_PDF_SUPPORT_ENABLED
from django_ledger.templatetags.django_ledger import currency_symbol, currency_format

if DJANGO_LEDGER_PDF_SUPPORT_ENABLED:
    from fpdf import FPDF, XPos, YPos


class PDFReportValidationError(ValidationError):
    pass


def load_support():
    support = list()
    if DJANGO_LEDGER_PDF_SUPPORT_ENABLED:
        support.append(FPDF)
    return support


class BaseReportSupport(*load_support()):
    FOOTER_LOGO_PATH = 'django_ledger/logo/django-ledger-logo-report.png'

    def __init__(self,
                 *args,
                 io_digest: IODigestContextManager,
                 report_subtitle: Optional[str] = None,
                 **kwargs):

        if not DJANGO_LEDGER_PDF_SUPPORT_ENABLED:
            raise NotImplementedError('PDF support not enabled.')

        super().__init__(*args, **kwargs)
        self.REPORT_TYPE: Optional[str] = None
        self.REPORT_SUBTITLE: Optional[str] = report_subtitle
        self.FONT_SIZE: int = 9
        self.FONT_FAMILY: str = 'helvetica'
        self.PAGE_WIDTH = 210
        self.IO_DIGEST: IODigestContextManager = io_digest
        self.CURRENCY_SYMBOL = currency_symbol()
        self.set_default_font()
        self.alias_nb_pages()
        self.add_page()
        self.TABLE_HEADERS: Optional[Dict]

    def set_default_font(self):
        self.set_font(
            family=self.FONT_FAMILY,
            size=self.FONT_SIZE
        )

    def header(self):
        # # Report Type
        self.set_font(
            family=self.FONT_FAMILY,
            size=self.FONT_SIZE + 2
        )
        w = self.get_string_width(self.get_report_name())
        self.set_x((self.PAGE_WIDTH - w) / 2)
        self.cell(w, 3, self.get_report_name(), ln=1)

        # Report Title
        self.set_font(
            family=self.FONT_FAMILY,
            size=self.FONT_SIZE + 6,
            style='B'
        )
        report_title = self.get_report_title()
        w = self.get_string_width(report_title)
        self.set_x((self.PAGE_WIDTH - w) / 2)
        self.cell(w=w,
                  h=6,
                  txt=report_title,
                  border=0,
                  new_x=XPos.LMARGIN,
                  new_y=YPos.NEXT,
                  align='C')

        if self.REPORT_SUBTITLE:
            self.set_font(
                family=self.FONT_FAMILY,
                size=self.FONT_SIZE,
                style='UI'
            )
            w = self.get_string_width(self.REPORT_SUBTITLE)
            self.set_x((self.PAGE_WIDTH - w) / 2)
            self.cell(w=w,
                      h=6,
                      txt=self.REPORT_SUBTITLE.title(),
                      border=0,
                      new_x=XPos.LMARGIN,
                      new_y=YPos.NEXT,
                      align='C')

        # Period
        self.set_font(
            family=self.FONT_FAMILY,
            size=self.FONT_SIZE - 1,
            style='I'
        )

        from_date = self.IO_DIGEST.get_from_date(as_str=True)
        to_date = self.IO_DIGEST.get_to_date(as_str=True)

        if from_date and to_date:
            period = f'From {from_date} through {to_date}'
        elif to_date:
            period = f'Through {to_date}'
        else:
            raise PDFReportValidationError('PDF report must have dates specified.')
        w = self.get_string_width(period)
        self.set_x((self.PAGE_WIDTH - w) / 2)
        self.cell(w=w,
                  h=5,
                  txt=period,
                  new_x=XPos.LMARGIN,
                  new_y=YPos.NEXT,
                  align='C')

        # Line break
        self.ln(10)
        self.set_default_font()

    def print_headers(self):
        for k, header in self.TABLE_HEADERS.items():
            self.set_font(
                family=self.FONT_FAMILY,
                style=header.get('style', ''),
                size=self.FONT_SIZE)
            w = self.get_string_width(header['title']) + header['spacing']
            self.cell(
                w=w,
                h=5,
                txt=header['title'],
                align=header['align'],
            )
        self.ln(8)
        self.set_default_font()

    def print_amount(self, amt, zoom=0):
        self.set_x(178)
        self.set_font(
            family=self.FONT_FAMILY,
            size=self.FONT_SIZE + zoom
        )
        self.cell(
            w=20,
            h=5,
            markdown=True,
            align='R',
            txt=f'**{self.CURRENCY_SYMBOL}{currency_format(amt)}**'
        )
        self.set_default_font()

    def print_hline(self):
        self.line(
            x1=self.get_x(),
            y1=self.get_y(),
            x2=self.get_x() + self.PAGE_WIDTH - 20,
            y2=self.get_y()
        )

    def get_report_title(self):
        if self.IO_DIGEST.is_entity_model():
            return self.IO_DIGEST.IO_MODEL.name
        elif self.IO_DIGEST.is_ledger_model():
            ledger_model: LedgerModel = self.IO_DIGEST.IO_MODEL
            if self.REPORT_SUBTITLE:
                return ledger_model.get_entity_name()
            return f'{ledger_model.get_entity_name()} | Ledger **{str(ledger_model.uuid)[-6:]}'
        elif self.IO_DIGEST.is_unit_model():
            unit_model: EntityUnitModel = self.IO_DIGEST.IO_MODEL
            if self.REPORT_SUBTITLE:
                return unit_model.get_entity_name()
            return f'{unit_model.get_entity_name()} | Unit {unit_model.name}'
        raise PDFReportValidationError('get_report_title() not implemented for'
                                       f' IO_MODEL {self.IO_DIGEST.IO_MODEL.__class__.__name__}')

    def get_report_name(self):
        raise NotImplementedError(f'Must define REPORT_TYPE on {self.__class__.__name__}')

    def get_report_data(self):
        raise NotImplementedError()

    def get_report_footer_logo_path(self) -> str:
        return finders.find(self.FOOTER_LOGO_PATH)

    def print_section_title(self, title, style='BU', zoom=4, w=160, align='L'):
        self.set_font(
            family=self.FONT_FAMILY,
            style=style,
            size=self.FONT_SIZE + zoom
        )
        # Assets title...
        self.cell(
            w=w,
            h=6,
            txt=title,
            align=align
        )
        self.set_default_font()

    def footer(self):
        self.set_y(-25)
        self.set_font(self.FONT_FAMILY, 'I', 8)
        self.cell(0, 5, 'Page ' + str(self.page_no()) + '/{nb}', 0, 1, 'C')
        self.set_font(family=self.FONT_FAMILY, size=self.FONT_SIZE - 3)
        self.image(self.get_report_footer_logo_path(),
                   w=30, x=(200 - 30) / 2,
                   link='https://www.djangoledger.com')
        self.ln(1)
        self.cell(0, 5,
                  'Powered by Django Ledger. Open Source software under GPLv3 License. '
                  'Created by Miguel Sanda <msanda@arrobalytics.com>',
                  0, 1, 'C')

    def create_pdf_report(self):
        raise NotImplementedError()

    def get_pdf_filename(self):
        raise NotImplementedError()
