from datetime import datetime
from calendar import monthrange


def monthend(dt):
    if isinstance(dt, datetime):
        return datetime(dt.year,
                        dt.month,
                        monthrange(dt.year, dt.month)[-1])
