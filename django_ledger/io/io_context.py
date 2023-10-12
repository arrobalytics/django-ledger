from collections import defaultdict
from itertools import groupby, chain

from django.core.exceptions import ValidationError

from django_ledger.io import roles as roles_module
from django_ledger.models.utils import LazyLoader, lazy_loader

lazy_importer = LazyLoader()


class RoleContextManager:

    def __init__(self,
                 io_data: dict,
                 by_period: bool = False,
                 by_unit: bool = False):

        self.BY_PERIOD = by_period
        self.BY_UNIT = by_unit

        self.DIGEST = io_data
        self.DIGEST['role_account'] = None
        self.DIGEST['role_balance'] = None

        self.ACCOUNTS = io_data['accounts']

        self.ROLES_ACCOUNTS = dict()
        self.ROLES_BALANCES = dict()
        self.ROLES_BALANCE_SHEET = dict()

        if self.BY_PERIOD:
            self.ROLES_BALANCES_BY_PERIOD = defaultdict(lambda: dict())
            self.DIGEST['role_balance_by_period'] = None
        if self.BY_UNIT:
            self.ROLES_BALANCES_BY_UNIT = defaultdict(lambda: dict())
            self.DIGEST['role_balance_by_unit'] = None

        if self.BY_PERIOD and self.BY_UNIT:
            self.ROLES_BALANCES_BY_PERIOD_AND_UNIT = defaultdict(lambda: dict())

    def digest(self):

        self.process_roles()
        self.DIGEST['role_account'] = self.ROLES_ACCOUNTS
        self.DIGEST['role_balance'] = self.ROLES_BALANCES

        if self.BY_PERIOD:
            self.DIGEST['role_balance_by_period'] = self.ROLES_BALANCES_BY_PERIOD
        if self.BY_UNIT:
            self.DIGEST['role_balance_by_unit'] = self.ROLES_BALANCES_BY_UNIT

        return self.DIGEST

    def process_roles(self):

        for c, l in roles_module.ROLES_DIRECTORY.items():
            for r in l:
                acc_list = list(acc for acc in self.ACCOUNTS if acc['role'] == getattr(roles_module, r))

                self.ROLES_ACCOUNTS[r] = acc_list
                self.ROLES_BALANCES[r] = sum(acc['balance'] for acc in acc_list)

                if self.BY_PERIOD or self.BY_UNIT:
                    for acc in acc_list:
                        if self.BY_PERIOD:
                            key = (acc['period_year'], acc['period_month'])
                            self.ROLES_BALANCES_BY_PERIOD[key][r] = sum(acc['balance'] for acc in acc_list if all([
                                acc['period_year'] == key[0],
                                acc['period_month'] == key[1]]
                            ))
                        if self.BY_UNIT:
                            key = (acc['unit_uuid'], acc['unit_name'])
                            self.ROLES_BALANCES_BY_UNIT[key][r] = sum(
                                acc['balance'] for acc in acc_list if acc['unit_uuid'] == key[0])


class GroupContextManager:
    GROUP_ACCOUNTS_KEY = 'group_account'
    GROUP_BALANCE_KEY = 'group_balance'
    GROUP_BALANCE_BY_UNIT_KEY = 'group_balance_by_unit'
    GROUP_BALANCE_BY_PERIOD_KEY = 'group_balance_by_period'

    def __init__(self,
                 io_data: dict,
                 by_period: bool = False,
                 by_unit: bool = False):

        self.BY_PERIOD = by_period
        self.BY_UNIT = by_unit

        self.IO_DIGEST = io_data

        self.IO_DIGEST[self.GROUP_ACCOUNTS_KEY] = None
        self.IO_DIGEST[self.GROUP_BALANCE_KEY] = None

        self.DIGEST_ACCOUNTS = io_data['accounts']

        self.GROUPS_ACCOUNTS = dict()
        self.GROUPS_BALANCES = dict()

        if self.BY_PERIOD:
            self.GROUPS_BALANCES_BY_PERIOD = defaultdict(lambda: dict())
            self.IO_DIGEST[self.GROUP_BALANCE_BY_PERIOD_KEY] = None

        if self.BY_UNIT:
            self.GROUPS_BALANCES_BY_UNIT = defaultdict(lambda: dict())
            self.IO_DIGEST[self.GROUP_BALANCE_BY_UNIT_KEY] = None

        if self.BY_PERIOD and self.BY_UNIT:
            self.GROUPS_BALANCES_BY_PERIOD_AND_UNIT = defaultdict(lambda: dict())
            self.IO_DIGEST[self.GROUP_BALANCE_BY_PERIOD_KEY] = None

    def digest(self):

        self.process_groups()
        self.IO_DIGEST[self.GROUP_ACCOUNTS_KEY] = self.GROUPS_ACCOUNTS
        self.IO_DIGEST[self.GROUP_BALANCE_KEY] = self.GROUPS_BALANCES

        if self.BY_PERIOD:
            self.IO_DIGEST[self.GROUP_BALANCE_BY_PERIOD_KEY] = self.GROUPS_BALANCES_BY_PERIOD
        if self.BY_UNIT:
            self.IO_DIGEST[self.GROUP_BALANCE_BY_UNIT_KEY] = self.GROUPS_BALANCES_BY_UNIT
        return self.IO_DIGEST

    def get_accounts_generator(self, mod, g):
        return (acc for acc in self.DIGEST_ACCOUNTS if acc['role'] in getattr(mod, g))

    def process_groups(self):
        for g in roles_module.ROLES_GROUPS:
            acc_list = list(self.get_accounts_generator(roles_module, g))
            self.GROUPS_ACCOUNTS[g] = acc_list
            self.GROUPS_BALANCES[g] = sum(acc['balance'] for acc in acc_list)

            if self.BY_PERIOD or self.BY_UNIT:
                for acc in acc_list:
                    if self.BY_PERIOD:
                        key = (acc['period_year'], acc['period_month'])
                        self.GROUPS_BALANCES_BY_PERIOD[key][g] = sum(
                            acc['balance'] for acc in acc_list if all([
                                acc['period_year'] == key[0],
                                acc['period_month'] == key[1]]
                            ))
                    if self.BY_UNIT:
                        key = (acc['unit_uuid'], acc['unit_name'])
                        self.GROUPS_BALANCES_BY_UNIT[key][g] = sum(
                            acc['balance'] for acc in acc_list if acc['unit_uuid'] == key[0]
                        )


class ActivityContextManager:

    def __init__(self,
                 io_data: dict,
                 by_unit: bool = False,
                 by_period: bool = False):

        self.DIGEST = io_data
        self.DIGEST['activity_account'] = None
        self.DIGEST['activity_balance'] = None

        self.BY_PERIOD = by_period
        self.BY_UNIT = by_unit

        self.ACCOUNTS = io_data['accounts']
        self.ACTIVITY_ACCOUNTS = dict()
        self.ACTIVITY_BALANCES = dict()

        if self.BY_PERIOD:
            self.ACTIVITY_BALANCES_BY_PERIOD = defaultdict(lambda: dict())
            self.DIGEST['activity_balance_by_period'] = None
        if self.BY_UNIT:
            self.ACTIVITY_BALANCES_BY_UNIT = defaultdict(lambda: dict())
            self.DIGEST['activity_balance_by_unit'] = None
        if self.BY_PERIOD and self.BY_UNIT:
            self.ROLES_BALANCES_BY_PERIOD_AND_UNIT = defaultdict(lambda: dict())

    def digest(self):

        self.process_activity()
        self.DIGEST['activity_account'] = self.ACTIVITY_ACCOUNTS
        self.DIGEST['activity_balance'] = self.ACTIVITY_BALANCES

        if self.BY_PERIOD:
            self.DIGEST['activity_balance_by_period'] = self.ACTIVITY_BALANCES_BY_PERIOD
        if self.BY_UNIT:
            self.DIGEST['activity_balance_by_unit'] = self.ACTIVITY_BALANCES_BY_PERIOD

    def get_accounts_generator(self, activity: str):
        return (acc for acc in self.ACCOUNTS if acc['activity'] == activity)

    def process_activity(self):
        JournalEntryModel = lazy_importer.get_journal_entry_model()
        for act in JournalEntryModel.VALID_ACTIVITIES:
            acc_list = list(self.get_accounts_generator(act))
            self.ACTIVITY_ACCOUNTS[act] = acc_list
            self.ACTIVITY_BALANCES[act] = sum(acc['balance'] for acc in acc_list)

            if self.BY_PERIOD or self.BY_UNIT:
                for acc in acc_list:
                    if self.BY_PERIOD:
                        key = (acc['period_year'], acc['period_month'])
                        self.ACTIVITY_BALANCES_BY_PERIOD[key][act] = sum(acc['balance'] for acc in acc_list if all([
                            acc['period_year'] == key[0],
                            acc['period_month'] == key[1]]
                        ))
                    if self.BY_UNIT:
                        key = (acc['unit_uuid'], acc['unit_name'])
                        self.ACTIVITY_BALANCES_BY_UNIT[key][act] = sum(
                            acc['balance'] for acc in acc_list if acc['unit_uuid'] == key[0])


class BalanceSheetStatementContextManager:
    def __init__(self, io_data: dict):
        self.DIGEST = io_data

    def digest(self):
        if 'group_account' in self.DIGEST:
            gb_bs = {
                bsr: list(l) for bsr, l in groupby(
                    chain.from_iterable(
                        [
                            self.DIGEST['group_account']['GROUP_ASSETS'],
                            self.DIGEST['group_account']['GROUP_LIABILITIES'],
                            self.DIGEST['group_account']['GROUP_CAPITAL'],
                        ]
                    ),
                    key=lambda acc: acc['role_bs'])
            }

            bs_context = {
                bs_role: {
                    'total_balance': sum(a['balance'] for a in gb),
                    'is_block': True,
                    'roles': {
                        r: {
                            'accounts': list(a)
                        } for r, a in groupby(list(gb), key=lambda acc: acc['role'])
                    }
                } for bs_role, gb in gb_bs.items()
            }

            for bs_role, bs_role_data in bs_context.items():
                for acc_role, role_data in bs_role_data['roles'].items():
                    role_data['total_balance'] = sum(a['balance'] for a in role_data['accounts'])
                    role_data['role_name'] = roles_module.ACCOUNT_LIST_ROLE_VERBOSE[acc_role]

            bs_context['equity_balance'] = self.DIGEST['group_balance']['GROUP_EQUITY']
            bs_context['retained_earnings_balance'] = self.DIGEST['group_balance']['GROUP_EARNINGS']
            bs_context['liabilities_equity_balance'] = self.DIGEST['group_balance']['GROUP_LIABILITIES_EQUITY']

            self.DIGEST['balance_sheet'] = bs_context

        return self.DIGEST


class IncomeStatementContextManager:

    def __init__(self, io_data: dict):
        self.DIGEST = io_data

    def digest(self):
        if 'group_account' in self.DIGEST:
            self.DIGEST['income_statement'] = {
                'operating': {
                    'revenues': [
                        acc for acc in self.DIGEST['group_account']['GROUP_INCOME'] if
                        acc['role'] in roles_module.GROUP_IC_OPERATING_REVENUES
                    ],
                    'cogs': [
                        acc for acc in self.DIGEST['group_account']['GROUP_COGS'] if
                        acc['role'] in roles_module.GROUP_IC_OPERATING_COGS
                    ],
                    'expenses': [
                        acc for acc in self.DIGEST['group_account']['GROUP_EXPENSES'] if
                        acc['role'] in roles_module.GROUP_IC_OPERATING_EXPENSES
                    ]
                },
                'other': {
                    'revenues': [acc for acc in self.DIGEST['group_account']['GROUP_INCOME'] if
                                 acc['role'] in roles_module.GROUP_IC_OTHER_REVENUES],
                    'expenses': [acc for acc in self.DIGEST['group_account']['GROUP_EXPENSES'] if
                                 acc['role'] in roles_module.GROUP_IC_OTHER_EXPENSES],
                }
            }

            for activity, ic_section in self.DIGEST['income_statement'].items():
                for section, acc_list in ic_section.items():
                    for acc in acc_list:
                        acc['role_name'] = roles_module.ACCOUNT_LIST_ROLE_VERBOSE[acc['role']]

            # OPERATING INCOME...
            self.DIGEST['income_statement']['operating']['gross_profit'] = sum(
                acc['balance'] for acc in chain.from_iterable(
                    [
                        self.DIGEST['income_statement']['operating']['revenues'],
                        self.DIGEST['income_statement']['operating']['cogs']
                    ]
                ))
            self.DIGEST['income_statement']['operating']['net_operating_income'] = sum(
                acc['balance'] for acc in chain.from_iterable(
                    [
                        self.DIGEST['income_statement']['operating']['revenues'],
                        self.DIGEST['income_statement']['operating']['cogs'],
                        self.DIGEST['income_statement']['operating']['expenses'],
                    ]
                ))
            self.DIGEST['income_statement']['operating']['net_operating_revenue'] = sum(
                acc['balance'] for acc in self.DIGEST['income_statement']['operating']['revenues']
            )
            self.DIGEST['income_statement']['operating']['net_cogs'] = sum(
                acc['balance'] for acc in self.DIGEST['income_statement']['operating']['cogs']
            )
            self.DIGEST['income_statement']['operating']['net_operating_expenses'] = sum(
                acc['balance'] for acc in self.DIGEST['income_statement']['operating']['expenses']
            )

            # OTHER INCOME....
            self.DIGEST['income_statement']['other']['net_other_revenues'] = sum(
                acc['balance'] for acc in self.DIGEST['income_statement']['other']['revenues']
            )
            self.DIGEST['income_statement']['other']['net_other_expenses'] = sum(
                acc['balance'] for acc in self.DIGEST['income_statement']['other']['expenses']
            )
            self.DIGEST['income_statement']['other']['net_other_income'] = sum(
                acc['balance'] for acc in chain.from_iterable(
                    [
                        self.DIGEST['income_statement']['other']['revenues'],
                        self.DIGEST['income_statement']['other']['expenses']
                    ]
                ))

            # NET INCOME...
            self.DIGEST['income_statement']['net_income'] = self.DIGEST['income_statement']['operating'][
                'net_operating_income']
            self.DIGEST['income_statement']['net_income'] += self.DIGEST['income_statement']['other'][
                'net_other_income']
        return self.DIGEST


class CashFlowStatementContextManager:
    CFS_DIGEST_KEY = 'cash_flow_statement'

    # todo: implement by period and by unit...
    def __init__(self,
                 io_data: dict,
                 by_period: bool = False,
                 by_unit: bool = False):
        self.IO_DIGEST = io_data
        self.CASH_ACCOUNTS = [a for a in self.IO_DIGEST['accounts'] if a['role'] == roles_module.ASSET_CA_CASH]
        self.JE_MODEL = lazy_loader.get_journal_entry_model()

    def check_io_digest(self):
        if GroupContextManager.GROUP_BALANCE_KEY not in self.IO_DIGEST:
            raise ValidationError(
                'IO Digest must have groups for Cash Flow Statement'
            )

    def operating(self):
        group_balances = self.IO_DIGEST[GroupContextManager.GROUP_BALANCE_KEY]
        operating_activities = dict()
        operating_activities['GROUP_CFS_NET_INCOME'] = {
            'description': 'Net Income',
            'balance': group_balances['GROUP_CFS_NET_INCOME']
        }
        operating_activities['GROUP_CFS_OP_DEPRECIATION_AMORTIZATION'] = {
            'description': 'Depreciation & Amortization of Assets',
            'balance': -group_balances['GROUP_CFS_OP_DEPRECIATION_AMORTIZATION']
        }
        operating_activities['GROUP_CFS_OP_INVESTMENT_GAINS'] = {
            'description': 'Gain/Loss Sale of Assets',
            'balance': group_balances['GROUP_CFS_OP_INVESTMENT_GAINS']
        }
        operating_activities['GROUP_CFS_OP_ACCOUNTS_RECEIVABLE'] = {
            'description': 'Accounts Receivable',
            'balance': -group_balances['GROUP_CFS_OP_ACCOUNTS_RECEIVABLE']
        }
        operating_activities['GROUP_CFS_OP_INVENTORY'] = {
            'description': 'Inventories',
            'balance': -group_balances['GROUP_CFS_OP_INVENTORY']
        }

        operating_activities['GROUP_CFS_OP_ACCOUNTS_PAYABLE'] = {
            'description': 'Accounts Payable',
            'balance': group_balances['GROUP_CFS_OP_ACCOUNTS_PAYABLE']
        }
        operating_activities['GROUP_CFS_OP_OTHER_CURRENT_ASSETS_ADJUSTMENT'] = {
            'description': 'Other Current Assets',
            'balance': -group_balances['GROUP_CFS_OP_OTHER_CURRENT_ASSETS_ADJUSTMENT']
        }
        operating_activities['GROUP_CFS_OP_OTHER_CURRENT_LIABILITIES_ADJUSTMENT'] = {
            'description': 'Other Current Liabilities',
            'balance': group_balances['GROUP_CFS_OP_OTHER_CURRENT_LIABILITIES_ADJUSTMENT']
        }

        net_cash_by_op_activities = sum(i['balance'] for g, i in operating_activities.items())
        self.IO_DIGEST[self.CFS_DIGEST_KEY]['operating'] = operating_activities
        self.IO_DIGEST[self.CFS_DIGEST_KEY]['net_cash_by_activity'] = dict(
            OPERATING=net_cash_by_op_activities
        )

    def financing(self):
        group_balances = self.IO_DIGEST[GroupContextManager.GROUP_BALANCE_KEY]
        financing_activities = dict()
        financing_activities['GROUP_CFS_FIN_ISSUING_EQUITY'] = {
            'description': 'Common Stock, Preferred Stock and Capital Raised',
            'balance': sum(a['balance'] for a in self.CASH_ACCOUNTS if a['activity'] == self.JE_MODEL.FINANCING_EQUITY)
        }
        financing_activities['GROUP_CFS_FIN_DIVIDENDS'] = {
            'description': 'Dividends Payed Out to Shareholders',
            'balance': sum(
                a['balance'] for a in self.CASH_ACCOUNTS if a['activity'] == self.JE_MODEL.FINANCING_DIVIDENDS)
        }
        financing_activities['GROUP_CFS_FIN_ST_DEBT_PAYMENTS'] = {
            'description': 'Increase/Reduction of Short-Term Debt Principal',
            'balance': sum(a['balance'] for a in self.CASH_ACCOUNTS if a['activity'] == self.JE_MODEL.FINANCING_STD)
        }
        financing_activities['GROUP_CFS_FIN_LT_DEBT_PAYMENTS'] = {
            'description': 'Increase/Reduction of Long-Term Debt Principal',
            'balance': sum(a['balance'] for a in self.CASH_ACCOUNTS if a['activity'] == self.JE_MODEL.FINANCING_LTD)
        }

        net_cash = sum(i['balance'] for g, i in financing_activities.items())
        self.IO_DIGEST[self.CFS_DIGEST_KEY]['financing'] = financing_activities
        self.IO_DIGEST[self.CFS_DIGEST_KEY]['net_cash_by_activity']['FINANCING'] = net_cash

    def investing(self):
        group_balances = self.IO_DIGEST[GroupContextManager.GROUP_BALANCE_KEY]
        investing_activities = dict()
        investing_activities['GROUP_CFS_INVESTING_SECURITIES'] = {
            'description': 'Purchase, Maturity and Sales of Investments & Securities',
            'balance': sum(
                a['balance'] for a in self.CASH_ACCOUNTS if a['activity'] == self.JE_MODEL.INVESTING_SECURITIES)
        }
        investing_activities['GROUP_CFS_INVESTING_PPE'] = {
            'description': 'Addition and Disposition of Property, Plant & Equipment',
            'balance': sum(
                a['balance'] for a in self.CASH_ACCOUNTS if a['activity'] == self.JE_MODEL.INVESTING_PPE)
        }

        net_cash = sum(i['balance'] for g, i in investing_activities.items())
        self.IO_DIGEST[self.CFS_DIGEST_KEY]['investing'] = investing_activities
        self.IO_DIGEST[self.CFS_DIGEST_KEY]['net_cash_by_activity']['INVESTING'] = net_cash

    def net_cash(self):
        self.IO_DIGEST[self.CFS_DIGEST_KEY]['net_cash'] = sum([
            bal for act, bal in self.IO_DIGEST[self.CFS_DIGEST_KEY]['net_cash_by_activity'].items()
        ])

    def digest(self):
        self.check_io_digest()
        self.operating()
        self.financing()
        self.investing()
        self.net_cash()
        return self.IO_DIGEST
