from calendar import monthrange
from datetime import datetime


def monthend(dt: datetime) -> datetime:
    return datetime(dt.year,
                    dt.month,
                    monthrange(dt.year, dt.month)[-1])
