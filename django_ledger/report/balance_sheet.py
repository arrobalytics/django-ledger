from typing import Optional, Dict

from django.urls import reverse

from django_ledger.io import IODigestContextManager
from django_ledger.report.core import BaseReportSupport, PDFReportValidationError
from django_ledger.settings import DJANGO_LEDGER_CURRENCY_SYMBOL
from django_ledger.templatetags.django_ledger import currency_symbol, currency_format


class BalanceSheetReport(BaseReportSupport):

    def __init__(self, *args, io_digest: IODigestContextManager, report_subtitle: Optional[str] = None, **kwargs):

        if not io_digest.has_balance_sheet():
            raise PDFReportValidationError('IO Digest does not have balance sheet information.')
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
                'align': 'R'
            }
        }
        for k, th in self.TABLE_HEADERS.items():
            th['width'] = self.get_string_width(th['title']) + th['spacing']

    def get_report_data(self) -> Dict:
        return self.IO_DIGEST.get_balance_sheet_data()

    def get_report_name(self) -> str:
        return 'Balance Sheet Statement'

    def print_section_data(self, section_data):

        for r, d in section_data['roles'].items():
            # # print role name...
            self.set_font(self.FONT_FAMILY, style='U', size=self.FONT_SIZE)
            self.set_x(15)
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
                    txt=''
                )
                self.cell(
                    w=self.TABLE_HEADERS['code']['width'],
                    h=account_height,
                    txt='      {code}'.format(code=acc['code'])
                )

                if acc['activity']:
                    act = ' '.join(acc['activity'].split('_')).lower()
                    self.cell(
                        w=self.TABLE_HEADERS['name']['width'],
                        h=account_height,
                        txt=f'{acc["name"]} ({act})'
                    )
                else:
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

            self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE)
            self.cell(
                w=20,
                h=2,
                txt='Total {r}'.format(r=d['role_name'])
            )

            self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE + 1)
            self.set_x(180)
            self.cell(
                w=20,
                h=2,
                align='R',
                txt='{s}{tot}'.format(s=currency_symbol(),
                                      tot=currency_format(d['total_balance']))
            )
            self.ln(3)
            self.print_hline()
            self.ln(5)

    def print_assets(self):

        self.print_section_title('Assets')
        self.ln(8)

        # accounts data....
        bs_data = self.IO_DIGEST.get_balance_sheet_data()
        section_data = bs_data.get('assets')

        if section_data:
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
        self.print_section_title('Liabilities')
        self.ln(8)

        # accounts data....
        bs_data = self.IO_DIGEST.get_balance_sheet_data()
        section_data = bs_data.get('liabilities')
        if section_data:
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
        self.ln(8)

        # accounts data....
        bs_data = self.IO_DIGEST.get_balance_sheet_data()
        section_data = bs_data.get('equity')

        if section_data:
            self.print_section_data(section_data)

        self.set_font(self.FONT_FAMILY, style='B', size=self.FONT_SIZE)
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
            txt='{s}{tot}'.format(r='Retained Earnings',
                                  s=currency_symbol(),
                                  tot=currency_format(bs_data['retained_earnings_balance']))
        )
        self.ln(h=3)
        self.print_hline()
        self.ln(5)

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

    def get_pdf_filename(self):
        dt_fmt = '%Y%m%d'
        f_name = f'{self.get_report_title()}_BalanceSheet_{self.IO_DIGEST.get_to_date(fmt=dt_fmt)}.pdf'
        return f_name

    def create_pdf_report(self):
        self.print_headers()
        self.print_assets()
        self.print_liabilities()
        self.print_equity()
