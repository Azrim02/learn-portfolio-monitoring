"""Positions and cash, built from trades. A position is never typed in."""
import csv
import datetime as dt
from dataclasses import dataclass

START_CASH = 1_000_000.0


@dataclass
class Position:
    quantity: float = 0.0       # traded
    settled: float = 0.0        # delivered
    cost: float = 0.0           # clean cost of the quantity, without fees
    realized: float = 0.0       # average cost method

    @property
    def avg_cost(self):
        return self.cost / self.quantity if self.quantity else 0.0


def read_trades(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    seen = set()
    for t in rows:
        for k in ("quantity", "price", "accrued", "fees"):
            t[k] = float(t[k])
        for k in ("trade_date", "settle_date"):
            t[k] = dt.date.fromisoformat(t[k])
        if t["id"] in seen or t["side"] not in ("BUY", "SELL") or t["quantity"] <= 0 \
                or t["settle_date"] < t["trade_date"]:
            raise ValueError(f"bad trade: {t}")
        seen.add(t["id"])
    return sorted(rows, key=lambda t: (t["trade_date"], t["id"]))


def cash_flow(trade, bonds=frozenset()):
    """Cash from one trade: negative for a purchase. Includes accrued interest and fees."""
    unit = 100 if trade["instrument"] in bonds else 1   # bonds are quoted per 100 of face
    sign = 1 if trade["side"] == "BUY" else -1
    return -sign * trade["quantity"] * (trade["price"] + trade["accrued"]) / unit - trade["fees"]


def build(trades, as_of, bonds=frozenset(), actions=(), coupons=()):
    """Return ({instrument: Position}, cash, income).

    actions: (instrument, ex_date, kind, amount). coupons: (instrument, pay_date, per 100).
    A trade on the ex-date does not get the dividend; a trade on the pay date does not
    get the coupon. Splits apply before trades on the ex-date.
    """
    events = [(a[1], 0, a) for a in actions if a[1] <= as_of]
    events += [(c[1], 0, (c[0], c[1], "coupon", c[2])) for c in coupons if c[1] <= as_of]
    events += [(t["trade_date"], 1, t) for t in trades if t["trade_date"] <= as_of]
    events.sort(key=lambda e: (e[0], e[1]))

    book, splits = {}, []
    cash = {"traded": START_CASH, "settled": START_CASH}
    income = {"dividend": 0.0, "coupon": 0.0, "fees": 0.0, "accrued_paid": 0.0}

    for _, kind, e in events:
        if kind == 0:
            i, day, what, amount = e
            p = book.get(i)
            if p is None:
                continue
            if what == "split":
                p.quantity *= amount
                splits.append((i, day, amount))
            else:
                # Pay dates of dividends are not in our data: the cash is booked on the ex-date.
                held = p.quantity if what == "dividend" else p.quantity / 100
                cash["traded"] += held * amount
                cash["settled"] += held * amount
                income[what] += held * amount
            continue

        p = book.setdefault(e["instrument"], Position())
        unit = 100 if e["instrument"] in bonds else 1
        sign = 1 if e["side"] == "BUY" else -1
        clean = e["quantity"] * e["price"] / unit
        accrued = e["quantity"] * e["accrued"] / unit
        if sign < 0:
            if e["quantity"] > p.quantity + 1e-9:
                raise ValueError(f"{e['id']} sells more than the position")
            share = e["quantity"] / p.quantity
            p.realized += clean - p.cost * share
            p.cost -= p.cost * share
        else:
            p.cost += clean
        p.quantity += sign * e["quantity"]
        flow = cash_flow(e, bonds)
        cash["traded"] += flow
        if e["settle_date"] <= as_of:
            cash["settled"] += flow
        income["fees"] -= e["fees"]
        income["accrued_paid"] -= sign * accrued

    for t in trades:
        if t["trade_date"] <= as_of and t["settle_date"] <= as_of:
            q = t["quantity"] * (1 if t["side"] == "BUY" else -1)
            for i, day, factor in splits:
                if i == t["instrument"] and day > t["trade_date"]:
                    q *= factor
            book[t["instrument"]].settled += q
    return book, cash, income
