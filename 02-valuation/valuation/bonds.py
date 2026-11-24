"""US Treasury note and bond maths. Prices are per 100 of face."""
import datetime as dt
from functools import lru_cache

import QuantLib as ql

from pipeline.dates import is_session

CALENDAR = ql.UnitedStates(ql.UnitedStates.GovernmentBond)


def qd(d):
    return ql.Date(d.day, d.month, d.year)


def pd(d):
    return dt.date(d.year(), d.month(), d.dayOfMonth())


@lru_cache(maxsize=None)
def bond(coupon, dated, maturity):
    end_of_month = ql.Date.isEndOfMonth(qd(maturity))
    schedule = ql.Schedule(qd(dated), qd(maturity), ql.Period(ql.Semiannual), ql.NullCalendar(),
                           ql.Unadjusted, ql.Unadjusted, ql.DateGeneration.Backward, end_of_month)
    count = ql.ActualActual(ql.ActualActual.ISMA, schedule)
    # Yield, price and accrued formulas use the unadjusted coupon dates.
    return ql.FixedRateBond(0, 100.0, schedule, [coupon / 100], count, ql.Unadjusted)


def settlement(trade_date):
    """T+1 on the bond calendar."""
    day = trade_date + dt.timedelta(days=1)
    while not is_session(day, "bond"):
        day += dt.timedelta(days=1)
    return day


def accrued(b, day):
    return b.accruedAmount(qd(day))


def _args(b):
    return b.dayCounter(), ql.Compounded, ql.Semiannual


def price_from_yield(b, y, settle):
    """Clean price. y in percent, bond-equivalent."""
    return ql.BondFunctions.cleanPrice(b, y / 100, *_args(b), qd(settle))


def yield_from_price(b, clean, settle):
    price = ql.BondPrice(clean, ql.BondPrice.Clean)
    return 100 * ql.BondFunctions.bondYield(b, price, *_args(b), qd(settle), 1e-12, 200, 0.05)


def modified_duration(b, y, settle):
    return ql.BondFunctions.duration(b, y / 100, *_args(b), ql.Duration.Modified, qd(settle))


def dv01(b, y, settle):
    """Change in price per 100 of face for a 1 bp fall in yield."""
    return (price_from_yield(b, y - 0.005, settle) - price_from_yield(b, y + 0.005, settle))


def _pay_date(c):
    """Cash due on a holiday arrives on the next business day."""
    return pd(CALENDAR.adjust(c.date(), ql.Following))


def cash_flows(b, after):
    return [(_pay_date(c), c.amount()) for c in b.cashflows() if pd(c.date()) > after]


def coupons(b):
    """(pay date, coupon per 100), without the principal."""
    return [(_pay_date(c), c.amount()) for c in list(b.cashflows())[:-1]]


def auction_price(b, y, issue):
    """Treasury auction formula (31 CFR 356): simple interest in the first part period.

    The secondary market formula, price_from_yield, uses compound interest there.
    """
    flows = [(pd(c.date()), c.amount()) for c in list(b.cashflows())[:-1] if pd(c.date()) > issue]
    first, coupon = flows[0]
    last = _period_start(b, issue)
    r, s = (first - issue).days, (first - last).days
    v, n = 1 / (1 + y / 200), len(flows) - 1
    dirty = (coupon * sum(v ** k for k in range(n + 1)) + 100 * v ** n) / (1 + r / s * y / 200)
    return dirty - accrued(b, issue)


def _period_start(b, day):
    for c in b.cashflows():
        c = ql.as_coupon(c)
        if c and pd(c.accrualStartDate()) <= day < pd(c.accrualEndDate()):
            return pd(c.accrualStartDate())
    raise ValueError(f"{day} is not in a coupon period")
