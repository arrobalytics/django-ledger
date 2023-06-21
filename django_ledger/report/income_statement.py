from typing import Optional, Dict

from django_ledger.io import IODigest
from django_ledger.report.core import BaseReportSupport, PDFReportValidationError
from django_ledger.settings import DJANGO_LEDGER_CURRENCY_SYMBOL
from django_ledger.templatetags.django_ledger import currency_symbol, currency_format


class IncomeStatementReport(BaseReportSupport):

    def __init__(self, *args, io_digest: IODigest, report_subtitle: Optional[str] = None, **kwargs):

        if not io_digest.has_income_statement():
            raise PDFReportValidationError('IO Digest does not have income statement information.')
        super().__init__(*args, io_digest=io_digest, report_subtitle=report_subtitle, **kwargs)
        self.TABLE_HEADERS = {
            'role': {
                'title': '',
                'spacing': 10,
                'align': 'L',
            },
            'code': {
                'title': 'Account Code',
                'spacing': 15,
                'align': 'L',
            },
            'name': {
                'title': 'Account Name',
                'spacing': 50,
                'align': 'C'
            },
            'balance_type': {
                'title': 'Balance Type',
                'spacing': 5,
                'align': 'C'
            },
            'balance': {
                'title': f'Balance ({DJANGO_LEDGER_CURRENCY_SYMBOL})',
                'spacing': 10,
                'align': 'R'
            },
            'total': {
                'title': f'Total ({DJANGO_LEDGER_CURRENCY_SYMBOL})',
                'spacing': 10,
                'align': 'R',
                'style': 'B'
            }
        }
        for k, th in self.TABLE_HEADERS.items():
            th['width'] = self.get_string_width(th['title']) + th['spacing']

    def get_report_data(self) -> Dict:
        return self.IO_DIGEST.get_income_statement_data()

    def get_report_name(self) -> str:
        return 'Income Statement'

    def print_section_data(self, section_data):

        account_height = 3
        self.set_font(self.FONT_FAMILY, size=self.FONT_SIZE)
        for acc in section_data:
            self.cell(
                w=self.TABLE_HEADERS['role']['width'],
                h=account_height,
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
                txt=f"{self.CURRENCY_SYMBOL}{currency_format(acc['balance_abs'])}"
            )
            self.ln(5)

    def print_operating_revenues(self):

        self.print_section_title('Operating Revenues')
        self.ln(8)

        ic_data = self.IO_DIGEST.get_income_statement_data()
        operating_section = ic_data['operating']
        self.print_section_data(operating_section['revenues'])
        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE)
        self.cell(
            w=20,
            h=2,
            txt='Net Operating Revenue'
        )
        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE + 1)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='{s}{tot}'.format(s=currency_symbol(),
                                  tot=currency_format(operating_section['net_operating_revenue']))
        )
        self.ln(h=3)
        self.print_hline()
        self.ln(5)

    def print_operating_cogs(self):
        self.print_section_title('LESS: Cost of Goods Sold')
        self.ln(8)

        ic_data = self.IO_DIGEST.get_income_statement_data()
        operating_section = ic_data['operating']
        self.print_section_data(operating_section['cogs'])
        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE)
        self.cell(
            w=20,
            h=2,
            txt='Net COGS'
        )
        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE + 1)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='{s}{tot}'.format(s=currency_symbol(),
                                  tot=currency_format(-operating_section['net_cogs']))
        )
        self.ln(h=3)
        self.print_hline()
        self.ln(5)

    def print_operating_gross_profit(self):
        ic_data = self.IO_DIGEST.get_income_statement_data()
        operating_section = ic_data['operating']

        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE + 2)
        self.cell(
            w=20,
            h=2,
            txt='Gross Profit (Op. Revenue - COGS)'
        )

        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE + 2)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='{s}{tot}'.format(s=currency_symbol(),
                                  tot=currency_format(operating_section['gross_profit']))
        )
        self.ln(h=3)
        self.print_hline()
        self.ln(5)

    def print_operating_expenses(self):

        self.print_section_title('Operating Expense')
        self.ln(8)

        ic_data = self.IO_DIGEST.get_income_statement_data()
        operating_section = ic_data['operating']
        self.print_section_data(operating_section['expenses'])
        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE)
        self.cell(
            w=20,
            h=2,
            txt='Net Operating Expense'
        )
        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE + 1)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='{s}{tot}'.format(s=currency_symbol(),
                                  tot=currency_format(-operating_section['net_operating_expenses']))
        )
        self.ln(h=3)
        self.print_hline()
        self.ln(5)

    def print_net_operating_income(self):
        ic_data = self.IO_DIGEST.get_income_statement_data()
        operating_section = ic_data['operating']
        self.set_font(self.FONT_FAMILY, style='BU', size=self.FONT_SIZE + 3)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='Net Operating Income (Loss): {s}{tot}'.format(s=currency_symbol(),
                                                               tot=currency_format(
                                                                   operating_section['net_operating_income']))
        )
        self.ln(h=5)

    def print_other_revenues(self):
        self.print_section_title('Other Revenues')
        self.ln(8)

        ic_data = self.IO_DIGEST.get_income_statement_data()
        other_section = ic_data['other']
        self.print_section_data(other_section['revenues'])
        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE)
        self.cell(
            w=20,
            h=2,
            txt='Net Other Revenue'
        )
        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE + 1)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='{s}{tot}'.format(s=currency_symbol(),
                                  tot=currency_format(other_section['net_other_revenues']))
        )
        self.ln(h=3)
        self.print_hline()
        self.ln(5)

    def print_other_expenses(self):
        self.print_section_title('Other Expenses')
        self.ln(8)

        ic_data = self.IO_DIGEST.get_income_statement_data()
        other_section = ic_data['other']
        self.print_section_data(other_section['expenses'])
        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE)
        self.cell(
            w=20,
            h=2,
            txt='Net Other Expenses'
        )
        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE + 1)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='{s}{tot}'.format(s=currency_symbol(),
                                  tot=currency_format(other_section['net_other_expenses']))
        )
        self.ln(h=3)
        self.print_hline()
        self.ln(5)

    def print_net_other_income(self):
        ic_data = self.IO_DIGEST.get_income_statement_data()
        operating_section = ic_data['other']
        self.set_font(self.FONT_FAMILY, style='BU', size=self.FONT_SIZE + 3)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='Net Other Income (Loss): {s}{tot}'.format(s=currency_symbol(),
                                                           tot=currency_format(
                                                               operating_section['net_other_income']))
        )
        self.ln(h=10)

    def print_net_income(self):
        ic_data = self.IO_DIGEST.get_income_statement_data()
        self.set_font(self.FONT_FAMILY, style='BU', size=self.FONT_SIZE + 3)
        self.set_x(180)
        self.cell(
            w=20,
            h=2,
            align='R',
            txt='Net Income (Loss): {s}{tot}'.format(s=currency_symbol(),
                                                     tot=currency_format(
                                                         ic_data['net_income']))
        )
        self.ln(h=5)

    def get_pdf_filename(self):
        dt_fmt = '%Y%m%d'
        f_name = f'{self.get_report_title()}_IncomeStatement_{self.IO_DIGEST.get_from_date(fmt=dt_fmt)}_'
        f_name += f'{self.IO_DIGEST.get_to_date(fmt=dt_fmt)}.pdf'
        return f_name

    def create_pdf_report(self):
        self.print_headers()
        self.print_operating_revenues()
        self.print_operating_cogs()
        self.print_operating_gross_profit()
        self.print_operating_expenses()
        self.print_net_operating_income()
        self.print_other_revenues()
        self.print_other_expenses()
        self.print_net_other_income()
        self.print_net_income()
