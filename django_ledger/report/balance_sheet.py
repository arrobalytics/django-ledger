from pathlib import Path

from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError

from django_ledger.io import IODigest
from django_ledger.settings import DJANGO_LEDGER_PDF_SUPPORT_ENABLED, DJANGO_LEDGER_CURRENCY_SYMBOL
from django_ledger.templatetags.django_ledger import currency_symbol, currency_format


def load_support():
    support = list()
    if DJANGO_LEDGER_PDF_SUPPORT_ENABLED:
        from fpdf import FPDF
        support.append(FPDF)
    return support


class BalanceSheetReportValidationError(ValidationError):
    pass


class BalanceSheetReport(*load_support()):
    FOOTER_LOGO_PATH = 'django_ledger/logo/django-ledger-logo-report.png'

    def __init__(self,
                 io_digest: IODigest,
                 font_size: int = 10,
                 font_family: str = 'Arial',
                 **kwargs):

        if not DJANGO_LEDGER_PDF_SUPPORT_ENABLED:
            raise NotImplementedError('PDF support not enabled.')

        super().__init__(**kwargs)

        if not io_digest.has_balance_sheet():
            raise BalanceSheetReportValidationError(
                'IO Digest does not have balance sheet information.'
            )

        self.IO_DIGEST: IODigest = io_digest
        self.REPORT_TYPE = 'Balance Sheet'
        self.CURRENCY_SYMBOL = currency_symbol()
        self.FONT_SIZE: int = font_size
        self.FONT_FAMILY: str = font_family
        self.TABLE_HEADERS = {
            'role': {
                'title': '',
                'spacing': 10,
            },
            'code': {
                'title': 'Account Code',
                'spacing': 15,
            },
            'name': {
                'title': 'Account Name',
                'spacing': 50,
                'align': 'C'
            },
            'balance_type': {
                'title': 'Balance Type',
                'spacing': 10,
                'align': 'C'
            },
            'balance': {
                'title': f'Balance ({DJANGO_LEDGER_CURRENCY_SYMBOL})',
                'spacing': 10,
                'align': 'R'
            },
            'total': {
                'title': f'Total ({DJANGO_LEDGER_CURRENCY_SYMBOL})',
                'spacing': 15,
                'align': 'R'
            }
        }

        self.alias_nb_pages()
        self.set_font(family=self.FONT_FAMILY, size=self.FONT_SIZE)

        for k, th in self.TABLE_HEADERS.items():
            th['width'] = self.get_string_width(th['title']) + th['spacing']

        self.add_page()

    def get_entity_title(self):
        if self.IO_DIGEST.is_entity_model():
            return self.IO_DIGEST.IO_MODEL.name

    def get_report_type(self):
        return self.REPORT_TYPE

    def get_report_footer_logo_path(self) -> Path:
        return finders.find(self.FOOTER_LOGO_PATH)

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
        period = self.IO_DIGEST.get_to_date().strftime('%m-%d-%Y')
        w = self.get_string_width(period)
        self.set_x((210 - w) / 2)
        self.cell(w=w,
                  h=5,
                  txt=f'Through {period}',
                  align='C')

        # Line break
        self.ln(10)

    def print_section_title(self, title):
        self.set_font(self.FONT_FAMILY, 'BU', self.FONT_SIZE + 4)

        # Assets title...
        self.cell(
            w=20,
            h=10,
            txt=title,
            ln=1

        )

    def print_section_data(self, section_data):

        for r, d in section_data['roles'].items():
            # # print role name...
            self.set_font(self.FONT_FAMILY, style='U', size=self.FONT_SIZE)
            self.cell(
                w=self.get_string_width(d['role_name']),
                h=2,
                txt=d['role_name']
            )
            self.ln(h=5)

            # for each account...
            self.set_font(self.FONT_FAMILY, size=self.FONT_SIZE)
            account_height = 3
            for acc in d['accounts']:
                self.cell(
                    w=self.TABLE_HEADERS['role']['width'],
                    h=account_height,
                    # txt=d['role_name']
                    txt=''
                )
                self.cell(
                    w=self.TABLE_HEADERS['code']['width'],
                    h=account_height,
                    txt='      {code}'.format(code=acc['code'])
                )
                self.cell(
                    w=self.TABLE_HEADERS['name']['width'],
                    h=account_height,
                    txt=acc['name']
                )
                self.cell(
                    w=self.TABLE_HEADERS['balance_type']['width'],
                    h=account_height,
                    txt=acc['balance_type'],
                    align='C'
                )
                self.cell(
                    w=self.TABLE_HEADERS['balance']['width'],
                    h=account_height,
                    align='R',
                    txt=f"{self.CURRENCY_SYMBOL}{currency_format(acc['balance'])}"
                )
                self.ln(5)

            self.set_font(self.FONT_FAMILY, style='BU', size=self.FONT_SIZE)
            self.cell(
                w=20,
                h=2,
                txt='Total {r}'.format(r=d['role_name'])
            )
            self.set_x(180)
            self.cell(
                w=20,
                h=2,
                align='R',
                txt='{space} {s}{tot}'.format(r=d['role_name'],
                                              space=' ' * 221,
                                              s=currency_symbol(),
                                              tot=currency_format(d['total_balance']))
            )
            self.ln(h=7)

    def print_headers(self):
        self.set_font(self.FONT_FAMILY, '', self.FONT_SIZE)
        for k, header in self.TABLE_HEADERS.items():
            w = self.get_string_width(header['title']) + header['spacing']
            self.cell(
                w=w,
                h=5,
                txt=header['title'],
                align=header.get('align')
            )
        self.ln(8)

    def print_assets(self):

        self.print_section_title('Assets')
        self.print_headers()

        # accounts data....
        bs_data = self.IO_DIGEST.get_balance_sheet_data()
        section_data = bs_data['assets']

        self.print_section_data(section_data)
        self.set_font(self.FONT_FAMILY, style='BU', size=self.FONT_SIZE + 3)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='Total Assets: {s}{tot}'.format(s=currency_symbol(),
                                                tot=currency_format(section_data['total_balance']))
        )
        self.ln(h=5)

    def print_liabilities(self):

        self.ln(10)

        self.print_section_title('Liabilities')
        self.print_headers()

        # accounts data....
        bs_data = self.IO_DIGEST.get_balance_sheet_data()
        section_data = bs_data['liabilities']

        self.print_section_data(section_data)
        self.set_font(self.FONT_FAMILY, style='BU', size=self.FONT_SIZE + 1)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='Total Liabilities: {s}{tot}'.format(s=currency_symbol(),
                                                     tot=currency_format(section_data['total_balance']))
        )
        self.ln(h=5)

    def print_equity(self):

        self.print_section_title('Equity')
        self.print_headers()

        # accounts data....
        bs_data = self.IO_DIGEST.get_balance_sheet_data()
        section_data = bs_data['equity']

        self.print_section_data(section_data)

        self.set_font(self.FONT_FAMILY, style='BU', size=self.FONT_SIZE)
        self.cell(
            w=20,
            h=2,
            txt='Retained Earnings'
        )
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='{space} {s}{tot}'.format(r='Retained Earnings',
                                          space=' ' * 221,
                                          s=currency_symbol(),
                                          tot=currency_format(bs_data['retained_earnings_balance']))
        )
        self.ln(h=7)

        self.set_font(self.FONT_FAMILY, style='BU', size=self.FONT_SIZE + 1)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='Total Equity: {s}{tot}'.format(s=currency_symbol(),
                                                tot=currency_format(bs_data['equity_balance']))
        )
        self.ln(h=10)

        self.set_font(self.FONT_FAMILY, style='BU', size=self.FONT_SIZE + 3)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='Total Liabilities + Equity: {s}{tot}'.format(s=currency_symbol(),
                                                              tot=currency_format(
                                                                  bs_data['liabilities_equity_balance']))
        )
        self.ln(h=5)

    def create_pdf_report(self):
        self.print_assets()
        self.print_liabilities()
        self.print_equity()

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
