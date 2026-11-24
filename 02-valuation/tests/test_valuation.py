import datetime as dt

import pytest
import valuation  # noqa: F401  (adds Project 1 to the path)
from valuation import bonds, curve, positions

D = dt.date
# Official auction results: coupon, dated, maturity, issue, yield, clean price, accrued per 100
OFFICIAL = [
    (4.625, D(2026, 8, 15), D(2036, 8, 15), D(2026, 8, 17), 4.683, 99.540696, 0.025136),
    (5.125, D(2026, 8, 15), D(2056, 8, 15), D(2026, 8, 17), 5.216, 98.627017, 0.027853),
    (4.625, D(2026, 8, 15), D(2036, 8, 15), D(2026, 9, 15), 4.834, 98.361116, 0.389606),
    (5.125, D(2026, 8, 15), D(2056, 8, 15), D(2026, 9, 15), 5.308, 97.262274, 0.431726),
    (4.625, D(2026, 8, 15), D(2036, 8, 15), D(2026, 10, 15), 5.300, 94.864261, 0.766644),
    (5.125, D(2026, 8, 15), D(2056, 8, 15), D(2026, 10, 15), 5.618, 92.889131, 0.849524),
    (4.750, D(2026, 9, 30), D(2028, 9, 30), D(2026, 9, 30), 4.787, 99.930225, 0.0),
    (5.000, D(2026, 9, 30), D(2031, 9, 30), D(2026, 9, 30), 5.033, 99.855714, 0.0),
]


@pytest.mark.parametrize("c,dated,mat,issue,y,price,acc", OFFICIAL)
def test_official_accrued(c, dated, mat, issue, y, price, acc):
    assert bonds.accrued(bonds.bond(c, dated, mat), issue) == pytest.approx(acc, abs=1e-6)


@pytest.mark.parametrize("c,dated,mat,issue,y,price,acc", OFFICIAL)
def test_official_price_and_yield_round_trip(c, dated, mat, issue, y, price, acc):
    b = bonds.bond(c, dated, mat)
    assert bonds.auction_price(b, y, issue) == pytest.approx(price, abs=1e-6)
    assert bonds.yield_from_price(b, bonds.price_from_yield(b, y, issue), issue) == pytest.approx(y, abs=1e-8)


def test_month_end_coupons():
    b = bonds.bond(4.75, D(2026, 9, 30), D(2028, 9, 30))
    assert [d for d, _ in bonds.cash_flows(b, D(2026, 9, 30))][0] == D(2027, 3, 31)


def test_holiday_moves_the_cash_but_not_the_formula():
    b = bonds.bond(4.75, D(2026, 9, 30), D(2028, 9, 30))   # 30 Sep 2028 is a Saturday
    assert bonds.cash_flows(b, D(2028, 4, 1))[-1][0] == D(2028, 10, 2)
    assert bonds.accrued(b, D(2028, 9, 30)) == pytest.approx(0)


def flat(y):
    return curve.Curve(D(2026, 11, 23), {t: y for t in (3, 6, 12, 24, 36, 60, 84, 120, 240, 360)})


def test_flat_curve_has_the_exact_discount_factor():
    assert flat(5.0).df_time(10) == pytest.approx(1.025 ** -20, rel=1e-12)


def test_bootstrap_reprices_its_own_par_bonds():
    c = curve.Curve(D(2026, 11, 23), {3: 4.37, 6: 4.45, 12: 4.57, 24: 4.63, 60: 4.74, 120: 4.92,
                                     240: 5.33, 360: 5.29})
    for n in (2, 4, 10, 20, 40, 60):
        pv = sum(c.par[n] / 2 * c.df_time(k / 2) for k in range(1, n + 1)) + 100 * c.df_time(n / 2)
        assert pv == pytest.approx(100, abs=1e-9)


def test_dv01_matches_duration():
    b = bonds.bond(4.625, D(2026, 8, 15), D(2036, 8, 15))
    s, y = D(2026, 11, 24), 4.92
    dirty = bonds.price_from_yield(b, y, s) + bonds.accrued(b, s)
    assert bonds.dv01(b, y, s) == pytest.approx(bonds.modified_duration(b, y, s) * dirty / 10000, rel=1e-5)


def trade(id, side, q, p, td, sd, i="X", accrued=0.0, fees=0.0):
    return {"id": id, "instrument": i, "side": side, "quantity": q, "price": p, "accrued": accrued,
            "fees": fees, "trade_date": td, "settle_date": sd}


def test_average_cost_and_realized():
    ts = [trade("1", "BUY", 10, 100, D(2026, 1, 5), D(2026, 1, 6)),
          trade("2", "BUY", 10, 120, D(2026, 1, 6), D(2026, 1, 7)),
          trade("3", "SELL", 5, 130, D(2026, 1, 7), D(2026, 1, 8), fees=2)]
    book, cash, _ = positions.build(ts, D(2026, 1, 7))
    p = book["X"]
    assert (p.quantity, p.settled, p.avg_cost, p.realized) == (15, 20, 110, 100)
    assert cash["traded"] == 1_000_000 - 2200 + 648
    assert cash["settled"] == 1_000_000 - 2200


def test_bond_cash_includes_accrued():
    _, cash, _ = positions.build([trade("1", "BUY", 100000, 99, D(2026, 1, 5), D(2026, 1, 6), accrued=0.5)],
                                 D(2026, 1, 6), bonds={"X"})
    assert cash["traded"] == 1_000_000 - 99_500


def test_dividend_needs_a_position_before_the_ex_date():
    ts = [trade("1", "BUY", 10, 100, D(2026, 1, 5), D(2026, 1, 6))]
    for ex, expected in ((D(2026, 1, 5), 0), (D(2026, 1, 6), 20)):
        _, _, income = positions.build(ts, D(2026, 1, 9), actions=[("X", ex, "dividend", 2.0)])
        assert income["dividend"] == expected


def test_split_keeps_cost_and_settled():
    ts = [trade("1", "BUY", 10, 100, D(2026, 1, 5), D(2026, 1, 6))]
    book, _, _ = positions.build(ts, D(2026, 1, 9), actions=[("X", D(2026, 1, 8), "split", 4.0)])
    p = book["X"]
    assert (p.quantity, p.settled, p.avg_cost, p.cost) == (40, 40, 25, 1000)


def test_oversell_is_rejected():
    with pytest.raises(ValueError):
        positions.build([trade("1", "SELL", 1, 100, D(2026, 1, 5), D(2026, 1, 6))], D(2026, 1, 6))
