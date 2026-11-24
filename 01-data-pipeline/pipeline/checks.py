"""Data quality checks.

A check takes (con, cfg, target) and returns a list of problem strings.
An empty list means PASS. Problems mean FAIL (bad data) or, for the checks in
WARN_ONLY, WARN (a person must look).
"""
import statistics

from . import config
from .dates import expected_date


def missing_values(con, cfg, target):
    """Every expected observation exists, after calendars and publication lags."""
    problems = []

    day = expected_date(target, "nyse")
    found = {r[0] for r in con.execute(
        "SELECT instrument_id FROM prices WHERE as_of = ? AND price_type = 'market'", [day]
    ).fetchall()}
    problems += [f"{i}: no market price for {day}"
                 for i in config.market_priced(cfg) if i not in found]

    curve = cfg["curve"]
    day = expected_date(target, curve["calendar"], curve["lag"])
    found = {r[0] for r in con.execute(
        "SELECT tenor_months FROM curves WHERE curve_id = ? AND as_of = ?", [curve["id"], day]
    ).fetchall()}
    problems += [f"{curve['id']} {t}m: no yield for {day}"
                 for t in curve["required_tenors"] if t not in found]

    for s in cfg["series"]:
        day = expected_date(target, s["calendar"], s["lag"])
        if not con.execute("SELECT 1 FROM series WHERE series_id = ? AND as_of = ?",
                           [s["id"], day]).fetchone():
            problems.append(f"{s['id']}: no value for {day}")

    problems += [f"{r[0]}: no security terms" for r in con.execute(
        "SELECT id FROM instruments WHERE type = 'treasury' AND "
        "(coupon IS NULL OR maturity IS NULL) ORDER BY id").fetchall()]
    return problems


def _closes(con, day):
    """Market closes up to day, newest first: {(instrument, source): [(date, price), ...]}."""
    out = {}
    for i, source, as_of, price in con.execute(
            "SELECT instrument_id, source, as_of, price FROM prices "
            "WHERE price_type = 'market' AND as_of <= ? ORDER BY as_of DESC", [day]).fetchall():
        out.setdefault((i, source), []).append((as_of, price))
    return out


def _split_factor(con, instrument, after, until):
    factor = 1.0
    for (amount,) in con.execute(
            "SELECT amount FROM corporate_actions WHERE instrument_id = ? AND kind = 'split' "
            "AND ex_date > ? AND ex_date <= ?", [instrument, after, until]).fetchall():
        factor *= amount
    return factor


def _return(con, instrument, new, old):
    """Split-adjusted return between two (date, price) pairs."""
    factor = _split_factor(con, instrument, old[0], new[0])
    return new[1] * factor / old[1] - 1


def stale_prices(con, cfg, target):
    """The close did not change for stale_sessions consecutive sessions.

    The rows must be on consecutive sessions: a missing row is a different problem.
    """
    n = cfg["checks"]["stale_sessions"]
    day = expected_date(target, "nyse")
    sessions = [expected_date(day, "nyse", lag) for lag in range(n + 1)]
    problems = []
    for (i, source), rows in _closes(con, day).items():
        last = rows[:n + 1]
        if [d for d, _ in last] == sessions and len({p for _, p in last}) == 1:
            problems.append(f"{i} ({source}): {last[0][1]} unchanged for {n} sessions")
    return problems


def outliers(con, cfg, target):
    """A move larger than a fixed limit: probably an error, so it FAILS."""
    limits, problems = cfg["checks"], []
    day = expected_date(target, "nyse")
    for (i, source), rows in _closes(con, day).items():
        if rows[0][0] == day and len(rows) > 1:
            r = _return(con, i, rows[0], rows[1])
            if abs(r) > limits["outlier_return"]:
                problems.append(f"{i} ({source}): {r:+.1%} since {rows[1][0]}")

    curve = cfg["curve"]
    day = expected_date(target, curve["calendar"], curve["lag"])
    for tenor, new, old in con.execute(
            "SELECT n.tenor_months, n.par_yield, o.par_yield FROM curves n JOIN curves o "
            "ON o.curve_id = n.curve_id AND o.tenor_months = n.tenor_months "
            "WHERE n.curve_id = ? AND n.as_of = ? AND o.as_of = "
            "(SELECT max(as_of) FROM curves WHERE curve_id = ? AND as_of < ?)",
            [curve["id"], day, curve["id"], day]).fetchall():
        bp = (new - old) * 100
        if abs(bp) > limits["outlier_curve_bp"]:
            problems.append(f"{curve['id']} {tenor:g}m: {bp:+.0f} bp")
    return problems


def unusual_moves(con, cfg, target):
    """A move that is large for this instrument: can be real, so it WARNS.

    The normal size is the standard deviation of the earlier returns only.
    """
    limits, problems = cfg["checks"], []
    day = expected_date(target, "nyse")
    for (i, source), rows in _closes(con, day).items():
        rows = rows[:limits["unusual_window"] + 2]
        if rows[0][0] != day or len(rows) < limits["unusual_min_history"] + 2:
            continue
        returns = [_return(con, i, a, b) for a, b in zip(rows, rows[1:])]
        sigma = statistics.stdev(returns[1:])
        if sigma and abs(returns[0]) > limits["unusual_sigma"] * sigma:
            problems.append(f"{i} ({source}): {returns[0]:+.2%} is {abs(returns[0]) / sigma:.1f} "
                            f"standard deviations; confirm it with a second source")
    return problems


def duplicate_sources(con, cfg, target):
    """Two sources disagree on the same instrument, date and price type."""
    day = expected_date(target, "nyse")
    tolerance = cfg["checks"]["duplicate_tolerance"]
    return [f"{i} {kind}: {low} and {high} from {n} sources" for i, kind, low, high, n in con.execute(
        "SELECT instrument_id, price_type, min(price), max(price), count(*) FROM prices "
        "WHERE as_of = ? GROUP BY 1, 2 HAVING count(*) > 1 AND max(price) / min(price) - 1 > ?",
        [day, tolerance]).fetchall()]


ALL = [missing_values, stale_prices, outliers, unusual_moves, duplicate_sources]
WARN_ONLY = {unusual_moves}


def run(con, cfg, target):
    results = []
    for check in ALL:
        problems = check(con, cfg, target)
        bad = "WARN" if check in WARN_ONLY else "FAIL"
        results.append((check.__name__, bad if problems else "PASS", problems))
    return results
