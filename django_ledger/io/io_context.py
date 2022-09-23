from collections import defaultdict

from django_ledger.io import roles as roles_module
from django_ledger.models.utils import LazyLoader

lazy_importer = LazyLoader()


class RoleManager:

    def __init__(self,
                 tx_digest: dict,
                 by_period: bool = False,
                 by_unit: bool = False):

        self.BY_PERIOD = by_period
        self.BY_UNIT = by_unit

        self.DIGEST = tx_digest
        self.DIGEST['role_account'] = None
        self.DIGEST['role_balance'] = None

        self.ACCOUNTS = tx_digest['accounts']

        self.ROLES_ACCOUNTS = dict()
        self.ROLES_BALANCES = dict()

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


class GroupManager:
    GROUP_ACCOUNTS_KEY = 'group_account'
    GROUP_BALANCE_KEY = 'group_balance'
    GROUP_BALANCE_BY_UNIT_KEY = 'group_balance_by_unit'
    GROUP_BALANCE_BY_PERIOD_KEY = 'group_balance_by_period'

    def __init__(self,
                 io_digest: dict,
                 by_period: bool = False,
                 by_unit: bool = False):

        self.BY_PERIOD = by_period
        self.BY_UNIT = by_unit

        self.IO_DIGEST = io_digest

        # todo: this is not necesary if io_digest is a defaultdict...
        self.IO_DIGEST[self.GROUP_ACCOUNTS_KEY] = None
        self.IO_DIGEST[self.GROUP_BALANCE_KEY] = None

        self.DIGEST_ACCOUNTS = io_digest['accounts']

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


class ActivityManager:

    def __init__(self,
                 tx_digest: dict,
                 by_unit: bool = False,
                 by_period: bool = False):

        self.DIGEST = tx_digest
        self.DIGEST['activity_account'] = None
        self.DIGEST['activity_balance'] = None

        self.BY_PERIOD = by_period
        self.BY_UNIT = by_unit

        self.ACCOUNTS = tx_digest['accounts']
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
