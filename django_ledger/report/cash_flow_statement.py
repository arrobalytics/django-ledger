from typing import Optional, Dict

from django_ledger.io import IODigest
from django_ledger.report.core import BaseReportSupport, PDFReportValidationError
from django_ledger.settings import DJANGO_LEDGER_CURRENCY_SYMBOL
from django_ledger.templatetags.django_ledger import currency_format


class CashFlowStatementReport(BaseReportSupport):

    def __init__(self, *args, io_digest: IODigest, report_subtitle: Optional[str] = None, **kwargs):

        if not io_digest.has_cash_flow_statement():
            raise PDFReportValidationError('IO Digest does not have income statement information.')
        super().__init__(*args, io_digest=io_digest, report_subtitle=report_subtitle, **kwargs)
        self.TABLE_HEADERS = {
            'empty_1': {
                'title': '',
                'spacing': 165,
                'align': 'L'
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
        return self.IO_DIGEST.get_cash_flow_statement_data()

    def get_report_name(self) -> str:
        return 'Cash Flow Statement'

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

    def print_starting_net_income(self):
        net_income = self.IO_DIGEST.IO_DATA['cash_flow_statement']['operating']['GROUP_CFS_NET_INCOME']['balance']
        self.print_section_title(
            title=f'Net Income as of {self.IO_DIGEST.get_from_date(as_str=True)}',
            style='B',
            w=170)
        self.print_amount(amt=net_income, zoom=2)
        self.ln(8)

    def print_cash_from_operating(self):
        self.print_section_title(title='Cash from Operating Activities', style='U')
        self.ln(7)

        self.set_x(40)
        self.print_section_title(title='Non-cash Charges to Non-current Accounts', style='', zoom=2)
        self.ln(5)

        self.set_x(50)
        self.print_section_title(title='Depreciation & Amortization of Assets', style='', zoom=0, align='R', w=100)
        amt = self.IO_DIGEST.IO_DATA['cash_flow_statement']['operating']['GROUP_CFS_OP_DEPRECIATION_AMORTIZATION'][
            'balance']
        self.print_amount(amt=amt)
        self.ln(5)

        self.set_x(50)
        self.print_section_title(title='Gain/Loss Sale of Assets', style='', zoom=0, align='R', w=100)
        amt = self.IO_DIGEST.IO_DATA['cash_flow_statement']['operating']['GROUP_CFS_OP_INVESTMENT_GAINS'][
            'balance']
        self.print_amount(amt=amt)
        self.ln(5)

        self.set_x(40)
        self.print_section_title(title='Non-cash Charges to Current Accounts', style='', zoom=2)
        self.ln(5)

        self.set_x(50)
        self.print_section_title(title='Accounts Receivable', style='', zoom=0, align='R', w=100)
        amt = self.IO_DIGEST.IO_DATA['cash_flow_statement']['operating']['GROUP_CFS_OP_ACCOUNTS_RECEIVABLE'][
            'balance']
        self.print_amount(amt=amt)
        self.ln(5)

        self.set_x(50)
        self.print_section_title(title='Inventories', style='', zoom=0, align='R', w=100)
        amt = self.IO_DIGEST.IO_DATA['cash_flow_statement']['operating']['GROUP_CFS_OP_INVENTORY'][
            'balance']
        self.print_amount(amt=amt)
        self.ln(5)

        self.set_x(50)
        self.print_section_title(title='Accounts Payable', style='', zoom=0, align='R', w=100)
        amt = self.IO_DIGEST.IO_DATA['cash_flow_statement']['operating']['GROUP_CFS_OP_ACCOUNTS_PAYABLE'][
            'balance']
        self.print_amount(amt=amt)
        self.ln(5)

        self.set_x(50)
        self.print_section_title(title='Other Current Assets', style='', zoom=0, align='R', w=100)
        amt = \
            self.IO_DIGEST.IO_DATA['cash_flow_statement']['operating']['GROUP_CFS_OP_OTHER_CURRENT_ASSETS_ADJUSTMENT'][
                'balance']
        self.print_amount(amt=amt)
        self.ln(5)

        self.set_x(50)
        self.print_section_title(title='Other Current Liabilities', style='', zoom=0, align='R', w=100)
        amt = \
            self.IO_DIGEST.IO_DATA['cash_flow_statement']['operating'][
                'GROUP_CFS_OP_OTHER_CURRENT_LIABILITIES_ADJUSTMENT'][
                'balance']
        self.print_amount(amt=amt)
        self.ln(5)

        self.print_hline()
        self.print_section_title(
            title='Net Cash Provided by Operating Activities',
            zoom=1,
            w=100,
            style='B'
        )
        amt = self.IO_DIGEST.IO_DATA['cash_flow_statement']['net_cash_by_activity']['OPERATING']
        self.print_amount(amt=amt, zoom=1)
        self.ln(12)

    def print_cash_from_financing(self):
        self.print_section_title(title='Cash from Financing Activities', style='U')
        self.ln(7)

        cf_section = self.IO_DIGEST.IO_DATA['cash_flow_statement']['financing']
        for _, sec in cf_section.items():
            self.set_x(50)
            self.print_section_title(
                title=sec['description'],
                style='',
                zoom=0,
                align='R',
                w=100)
            self.print_amount(
                amt=sec['balance'])
            self.ln(5)

        self.print_hline()
        self.print_section_title(
            title='Net Cash Provided by Financing Activities',
            zoom=1,
            w=100,
            style='B'
        )
        amt = self.IO_DIGEST.IO_DATA['cash_flow_statement']['net_cash_by_activity']['FINANCING']
        self.print_amount(amt=amt, zoom=1)
        self.ln(12)

    def print_cash_from_investing(self):
        self.print_section_title(title='Cash from Investing Activities', style='U')
        self.ln(7)

        cf_section = self.IO_DIGEST.IO_DATA['cash_flow_statement']['investing']
        for _, sec in cf_section.items():
            self.set_x(50)
            self.print_section_title(
                title=sec['description'],
                style='',
                zoom=0,
                align='R',
                w=100)
            self.print_amount(
                amt=sec['balance'])
            self.ln(5)

        self.print_hline()
        self.print_section_title(
            title='Net Cash Provided by Investing Activities',
            zoom=1,
            w=100,
            style='B'
        )
        amt = self.IO_DIGEST.IO_DATA['cash_flow_statement']['net_cash_by_activity']['INVESTING']
        self.print_amount(amt=amt, zoom=1)
        self.ln(12)

    def print_net_cash_flow(self):
        self.print_section_title(title='Net Cash Flow', style='U')
        self.ln(7)

        self.set_x(50)
        self.print_section_title(
            title=f'Net Cash Flow from {self.IO_DIGEST.get_from_date(as_str=True)} '
                  f'through {self.IO_DIGEST.get_to_date(as_str=True)}',
            style='',
            zoom=0,
            align='R',
            w=100)
        self.print_amount(
            amt=self.IO_DIGEST.IO_DATA['cash_flow_statement']['net_cash'],
            zoom=3
        )
        self.ln(5)

    def get_pdf_filename(self):
        dt_fmt = '%Y%m%d'
        f_name = f'{self.get_report_title()}_CashFlowStatement_{self.IO_DIGEST.get_from_date(fmt=dt_fmt)}-'
        f_name += f'{self.IO_DIGEST.get_to_date(fmt=dt_fmt)}.pdf'
        return f_name

    def create_pdf_report(self):
        self.print_headers()
        self.print_starting_net_income()
        self.print_cash_from_operating()
        self.print_cash_from_financing()
        self.print_cash_from_investing()
        self.print_net_cash_flow()
