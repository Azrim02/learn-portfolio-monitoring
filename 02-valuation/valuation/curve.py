"""From par yields to discount factors.

A par yield is the coupon of a bond that costs exactly 100. It is not the rate for
one cash flow. The bootstrap finds the discount factor of each half-year in turn:

    100 = c/2 * (DF1 + ... + DFn) + 100 * DFn
"""
import bisect
import datetime as dt
import math

import QuantLib as ql


class Curve:
    def __init__(self, as_of, par):
        """par: {tenor in months: par yield in percent}."""
        self.as_of = as_of
        tenors = sorted(t for t in par if t >= 6)
        if tenors[0] != 6 or tenors[-1] != 360:
            raise ValueError("the curve needs the 6 month and the 30 year par yields")
        smooth = ql.MonotonicCubicNaturalSpline(tenors, [par[t] for t in tenors])
        self.par = {n: smooth(6 * n) for n in range(1, 61)}   # n half-years

        self.times, self.logs, annuity = [0.0], [0.0], 0.0
        for t in sorted(t for t in par if t < 6):             # bills: simple interest
            self.times.append(t / 12)
            self.logs.append(-math.log(1 + par[t] / 100 * t / 12))
        for n in range(1, 61):
            c = self.par[n] / 200
            df = (1 - c * annuity) / (1 + c)
            annuity += df
            self.times.append(n / 2)
            self.logs.append(math.log(df))

    def df_time(self, t):
        """Log-linear: the forward rate is constant between two points."""
        if t <= 0:
            return 1.0
        i = min(bisect.bisect_left(self.times, t), len(self.times) - 1)
        t0, t1, l0, l1 = self.times[i - 1], self.times[i], self.logs[i - 1], self.logs[i]
        return math.exp(l0 + (l1 - l0) * (t - t0) / (t1 - t0))

    def df(self, day: dt.date):
        return self.df_time((day - self.as_of).days / 365.25)


def model_clean_price(curve, b, settle):
    from . import bonds
    dirty = sum(a * curve.df(d) for d, a in bonds.cash_flows(b, settle)) / curve.df(settle)
    return dirty - bonds.accrued(b, settle)


def load(con, as_of):
    """The last curve on or before as_of."""
    day = con.execute("SELECT max(as_of) FROM curves WHERE curve_id = 'UST_PAR' AND as_of <= ?",
                      [as_of]).fetchone()[0]
    par = dict(con.execute("SELECT tenor_months, par_yield FROM curves "
                           "WHERE curve_id = 'UST_PAR' AND as_of = ?", [day]).fetchall())
    return Curve(day, par)
