"""Business days. The stock and bond markets do not share all holidays."""
import datetime as dt
from zoneinfo import ZoneInfo

import QuantLib as ql

_CALENDARS = {
    "nyse": ql.UnitedStates(ql.UnitedStates.NYSE),
    "bond": ql.UnitedStates(ql.UnitedStates.GovernmentBond),
}
NEW_YORK = ZoneInfo("America/New_York")


def is_session(day, calendar):
    return _CALENDARS[calendar].isBusinessDay(ql.Date(day.day, day.month, day.year))


def expected_date(target, calendar, lag=0):
    """Latest observation that should exist for target, after the publication lag."""
    day = target
    while not is_session(day, calendar):
        day -= dt.timedelta(days=1)
    for _ in range(lag):
        day -= dt.timedelta(days=1)
        while not is_session(day, calendar):
            day -= dt.timedelta(days=1)
    return day


def last_complete_session(now=None):
    """Last NYSE session that ended. Before 19:00 New York, today is not complete."""
    now = (now or dt.datetime.now(NEW_YORK)).astimezone(NEW_YORK)
    day = now.date() if now.hour >= 19 else now.date() - dt.timedelta(days=1)
    return expected_date(day, "nyse")
