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

    def __init__(self, io_digest: IODigest, **kwargs):

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
        self.TABLE_HEADERS = [
            {
                'title': 'Account Code',
                'key': 'code',
                'spacing': 10,
            },
            {
                'title': 'Account Role',
                'spacing': 15,
                'key': 'role',
                # 'align': 'C'
            },
            {
                'title': 'Account Name',
                'spacing': 40,
                'key': 'name',
                'align': 'C'
            },
            {
                'title': 'Balance Type',
                'spacing': 10,
                'key': 'balance_type',
                'align': 'C'
            },
            {
                'title': f'Balance ({DJANGO_LEDGER_CURRENCY_SYMBOL})',
                'spacing': 10,
                'key': 'balance',
                'align': 'R'
            }
        ]

    def get_entity_title(self):
        if self.IO_DIGEST.is_entity_model():
            return self.IO_DIGEST.IO_MODEL.name

    def get_report_type(self):
        return self.REPORT_TYPE

    def header(self):
        self.set_font(
            family='Arial',
            style='B',
            size=10)

        # Report Type
        self.set_font(
            family='Arial',
            size=8
        )
        w = self.get_string_width(self.get_report_type())
        self.set_x((210 - w) / 2)
        self.cell(w, 3, self.get_report_type(), ln=1)

        # Report Title
        self.set_font(
            family='Arial',
            size=12,
            style='B'
        )
        entity_title = self.get_entity_title()
        w = self.get_string_width(entity_title)
        self.set_x((210 - w) / 2)
        self.cell(w=w,
                  h=4,
                  txt=entity_title,
                  border=0,
                  ln=1,
                  align='C')

        # Period
        self.set_font(
            family='Arial',
            size=8,
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

    def print_assets(self):
        self.add_page()
        self.set_font('Arial', 'BU', 14)

        # Assets title...
        self.cell(
            w=20,
            h=10,
            txt='Assets',
            ln=1

        )

        # table headers...
        widths = dict()
        self.set_font('Arial', '', 10)
        for header in self.TABLE_HEADERS:
            w = self.get_string_width(header['title']) + header['spacing']
            self.cell(
                w=w,
                h=5,
                txt=header['title'],
                align=header.get('align')
            )
            widths[header['key']] = w
        self.ln(8)

        # accounts data....
        bs_data = self.IO_DIGEST.get_balance_sheet_data()
        assets_data = bs_data['assets']

        # for each role...
        for r, d in assets_data['roles'].items():

            # # print role name...
            # self.set_font('Arial', style='U', size=9)
            # self.cell(self.get_string_width(
            #     d['role_name']
            # ), 3, d['role_name'])
            # self.ln(h=5)

            # for each account...
            self.set_font('Arial', size=10)
            account_height = 3
            for acc in d['accounts']:
                self.cell(
                    w=widths['code'],
                    h=account_height,
                    txt='      {code}'.format(code=acc['code'])
                )
                self.cell(
                    w=widths['role'],
                    h=account_height,
                    txt=d['role_name']
                )
                self.cell(
                    w=widths['name'],
                    h=account_height,
                    txt=acc['name']
                )
                self.cell(
                    w=widths['balance_type'],
                    h=account_height,
                    txt=acc['balance_type'],
                    align='C'
                )
                self.cell(
                    w=widths['balance'],
                    h=account_height,
                    align='R',
                    txt=f"{self.CURRENCY_SYMBOL}{currency_format(acc['balance'])}"
                )
                self.ln(5)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

