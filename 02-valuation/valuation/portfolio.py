"""Value the book on one date."""
from . import bonds, curve as curves, positions


def treasury(con, instrument):
    return bonds.bond(*con.execute(
        "SELECT coupon, dated_date, maturity FROM instruments WHERE id = ?", [instrument]).fetchone())


def value(con, trades, as_of):
    info = {r[0]: r[1:] for r in con.execute("SELECT id, type, sector FROM instruments").fetchall()}
    held = {t["instrument"] for t in trades}
    unknown = held - set(info)
    if unknown:
        raise ValueError(f"no instrument record: {sorted(unknown)}")
    ust = {i: treasury(con, i) for i in held if info[i][0] == "treasury"}
    actions = con.execute("SELECT instrument_id, ex_date, kind, amount FROM corporate_actions").fetchall()
    coupons = [(i, d, a) for i, b in ust.items() for d, a in bonds.coupons(b)]
    book, cash, income = positions.build(trades, as_of, set(ust), actions, coupons)

    curve = curves.load(con, as_of)
    first_settle = {}
    for t in trades:
        first_settle.setdefault(t["instrument"], t["settle_date"])
    rows = []
    for i, p in sorted(book.items()):
        if abs(p.quantity) < 1e-9:
            continue
        row = {"id": i, "type": info[i][0], "sector": info[i][1], "quantity": p.quantity,
               "settled": p.settled, "avg_cost": p.avg_cost, "realized": p.realized,
               "accrued": 0.0, "ytm": None, "duration": None, "dv01": None}
        if i in ust:
            b, face = ust[i], p.quantity / 100
            # A when-issued bond has no accrual yet: value it at its first settlement.
            settle = max(bonds.settlement(as_of), first_settle[i])
            accrual_day = max(as_of, first_settle[i])
            price, kind, day = curves.model_clean_price(curve, b, settle), "model", curve.as_of
            row["ytm"] = bonds.yield_from_price(b, price, settle)
            row["duration"] = bonds.modified_duration(b, row["ytm"], settle)
            row["dv01"] = bonds.dv01(b, row["ytm"], settle) * face
            row["accrued"] = bonds.accrued(b, accrual_day) * face
            row["avg_cost"] *= 100
            clean = price * face
        else:
            found = con.execute(
                "SELECT price, as_of FROM prices WHERE instrument_id = ? AND price_type = 'market' "
                "AND as_of <= ? ORDER BY as_of DESC LIMIT 1", [i, as_of]).fetchone()
            if not found:
                raise ValueError(f"{i}: no price on or before {as_of}")
            price, day = found
            kind, clean = "market", price * p.quantity
        row.update(price=price, price_type=kind, price_date=day, clean=clean,
                   value=clean + row["accrued"], unrealized=clean - p.cost)
        rows.append(row)

    nav = sum(r["value"] for r in rows) + cash["traded"]
    for r in rows:
        r["weight"] = r["value"] / nav
    return {"as_of": as_of, "curve_date": curve.as_of, "rows": rows, "cash": cash, "nav": nav,
            "income": income, "realized": sum(p.realized for p in book.values()),
            "dv01": sum(r["dv01"] or 0 for r in rows)}


def identity_gap(v):
    """NAV must equal start cash plus each source of P&L. Returns the difference."""
    explained = (positions.START_CASH + v["realized"] + sum(r["unrealized"] for r in v["rows"])
                 + sum(r["accrued"] for r in v["rows"]) + sum(v["income"].values()))
    return v["nav"] - explained
