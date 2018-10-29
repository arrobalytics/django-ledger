from datetime import datetime, date

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from .utils import monthend


class IOPreProcMixIn:

    def preproc_dates(self, start_date, end_date=None, years=None, months=None, days=None, return_monthend=False):
        """
        :return: start_date & end_date as Datetime objects.
        """

        if not isinstance(start_date, (datetime, date)):
            start_date = parse(start_date)
        if end_date and not isinstance(end_date, (datetime, date)):
            end_date = parse(end_date)
        if all([start_date, end_date]):
            return start_date, end_date
        else:

            if any([years, months, days]):
                end_date = start_date + relativedelta(years=years or 0,
                                                      months=months or 0,
                                                      days=days or 0)

        if return_monthend:
            start_date = monthend(start_date)
            if end_date:
                end_date = monthend(end_date)

        return start_date, end_date or None

    def preproc_je(self, start_date, end_date=None, plus_years=None, plus_months=None, plus_days=None,
                   desc=None, origin=None):
        """
        Pre-processing for all JEs. Will take dates as strings, parse and return datetime.
        Returns concatenation of JE description + origin for documenting JE.

        :param ledger:
        :param plus_years:
        :param plus_months:
        :param plus_days:
        :param start_date: As a string or datetime.
        :param end_date: As a string or datetime.
        :param desc: Description for the JE. Will be appended to 'origin' of JE.
        :param origin: Origin of the transaction.
        :return: Start and end dates as datetime objects, desc + origin parameter.
        """

        start_date, end_date = self.preproc_dates(start_date=start_date,
                                                  end_date=end_date,
                                                  years=plus_years,
                                                  months=plus_months,
                                                  days=plus_days)

        if not desc:
            desc = getattr(self, 'ledger').name
        if origin:
            desc = desc + '-' + origin

        return start_date, end_date, desc
