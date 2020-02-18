from django_ledger.io import roles as roles

RATIO_NA = 'NA'


class FinancialRatioManager:

    def __init__(self, tx_digest):
        self.DIGEST = tx_digest
        self.ACCOUNTS = tx_digest['accounts']
        self.RATIO_NA = RATIO_NA

        self.quick_assets = sum([acc['balance'] for acc in self.ACCOUNTS if acc['role'] in roles.GROUP_QUICK_ASSETS])
        self.current_liabilities = sum(
            [acc['balance'] for acc in self.ACCOUNTS if acc['role'] in roles.GROUP_CURRENT_LIABILITIES])
        self.current_assets = sum(
            [acc['balance'] for acc in self.ACCOUNTS if acc['role'] in roles.GROUP_CURRENT_ASSETS])
        self.equity = sum([acc['balance'] for acc in self.ACCOUNTS if acc['role'] in roles.GROUP_CAPITAL])
        self.debt = sum([acc['balance'] for acc in self.ACCOUNTS if acc['role'] in roles.GROUP_LIABILITIES])

        self.net_income = sum([acc['balance'] for acc in self.ACCOUNTS if acc['role'] in roles.GROUP_EARNINGS])
        self.net_sales = sum([acc['balance'] for acc in self.ACCOUNTS if acc['role'] in roles.GROUP_NET_SALES])
        self.net_profit = sum([acc['balance'] for acc in self.ACCOUNTS if acc['role'] in roles.GROUP_NET_PROFIT])
        self.gross_profit = sum([acc['balance'] for acc in self.ACCOUNTS if acc['role'] in roles.GROUP_GROSS_PROFIT])
        self.assets = sum([acc['balance'] for acc in self.ACCOUNTS if acc['role_bs'] == 'assets'])

        self.RATIOS = dict()

    def generate(self):
        self.quick_ratio()
        self.current_ratio()
        self.debt_to_equity()
        self.return_on_equity()
        self.return_on_assets()
        self.net_profit_margin()
        self.gross_profit_margin()
        self.DIGEST['ratios'] = self.RATIOS
        return self.DIGEST

    def quick_ratio(self, as_percent=False):
        if self.current_liabilities == 0:
            cr = self.RATIO_NA
        else:
            cr = self.quick_assets / self.current_liabilities
            if as_percent:
                cr = cr * 100
        self.RATIOS['quick_ratio'] = cr

    def current_ratio(self, as_percent=False):
        if self.current_liabilities == 0:
            cr = RATIO_NA
        else:
            cr = self.current_assets / self.current_liabilities
            if as_percent:
                cr = cr * 100
        self.RATIOS['current_ratio'] = cr

    def debt_to_equity(self, as_percent=False):
        if self.equity == 0:
            cr = RATIO_NA
        else:
            cr = self.debt / self.equity
            if as_percent:
                cr = cr * 100
        self.RATIOS['debt_to_equity'] = cr

    def return_on_equity(self, as_percent=False):
        if self.equity == 0:
            cr = RATIO_NA
        else:
            cr = self.net_income / self.equity
            if as_percent:
                cr = cr * 100
        self.RATIOS['return_on_equity'] = cr

    def return_on_assets(self, as_percent=False):
        if self.assets == 0:
            cr = RATIO_NA
        else:
            cr = self.net_income / self.assets
            if as_percent:
                cr = cr * 100
        self.RATIOS['return_on_assets'] = cr

    def net_profit_margin(self, as_percent=False):
        if self.net_sales == 0:
            npm = RATIO_NA
        else:
            npm = self.net_profit / self.net_sales
            if as_percent:
                npm = npm * 100
        self.RATIOS['net_profit_margin'] = npm

    def gross_profit_margin(self, as_percent=False):
        if self.gross_profit == 0:
            gpm = RATIO_NA
        else:
            gpm = self.gross_profit / self.net_sales
            if as_percent:
                gpm = gpm * 100
        self.RATIOS['gross_profit_margin'] = gpm

# PROFITABILITY RATIOS

# SOLVENCY RATIOS

# LEVERAGE RATIOS
