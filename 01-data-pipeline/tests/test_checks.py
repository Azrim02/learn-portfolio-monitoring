import datetime as dt

from conftest import TARGET, price
from pipeline import checks, db
from pipeline.dates import expected_date

def test_stale_passes_on_clean_data(con, cfg):
    assert checks.stale_prices(con, cfg, TARGET) == []


def test_stale_finds_frozen_price(con, cfg):
    db.upsert(con, "prices", [price(dt.date(2026, 11, d), 349.08) for d in (18, 19, 20)])
    assert checks.stale_prices(con, cfg, TARGET)


def test_outlier_passes_on_clean_data(con, cfg):
    assert checks.outliers(con, cfg, TARGET) == []


def test_outlier_finds_corrupted_price(con, cfg):
    db.upsert(con, "prices", [price(TARGET, 3490.80)])   # decimal point error
    assert checks.outliers(con, cfg, TARGET)


def test_outlier_finds_curve_jump(con, cfg):
    con.execute("UPDATE curves SET par_yield = 5.63 WHERE as_of = ?", [TARGET])
    assert checks.outliers(con, cfg, TARGET)


def test_outlier_accepts_a_split(con, cfg):
    db.upsert(con, "prices", [price(TARGET, 87.27)])
    db.upsert(con, "corporate_actions", [{"instrument_id": "AAPL", "ex_date": TARGET,
                                          "kind": "split", "amount": 4.0}])
    assert checks.outliers(con, cfg, TARGET) == []


def test_duplicate_passes_on_clean_data(con, cfg):
    assert checks.duplicate_sources(con, cfg, TARGET) == []


def test_duplicate_finds_disagreement(con, cfg):
    db.upsert(con, "prices", [price(TARGET, 355.0, source="other")])
    assert checks.duplicate_sources(con, cfg, TARGET)


def test_stale_ignores_a_gap(con, cfg):
    db.upsert(con, "prices", [price(dt.date(2026, 11, d), 349.08) for d in (18, 20)])
    con.execute("DELETE FROM prices WHERE as_of = ?", [dt.date(2026, 11, 19)])
    assert checks.stale_prices(con, cfg, TARGET) == []


def history(con, last_price):
    """100 sessions that move +1% and -1%, then the target price."""
    value, rows = 100.0, []
    for lag in range(100, 0, -1):
        value *= 1.01 if lag % 2 else 1 / 1.01
        rows.append(price(expected_date(TARGET, "nyse", lag), value))
    db.upsert(con, "prices", rows + [price(TARGET, last_price * value)])


def test_unusual_finds_a_move_below_the_fixed_limit(con, cfg):
    history(con, 1.06)
    assert checks.outliers(con, cfg, TARGET) == []
    assert checks.unusual_moves(con, cfg, TARGET)


def test_unusual_accepts_a_normal_move(con, cfg):
    history(con, 1.02)
    assert checks.unusual_moves(con, cfg, TARGET) == []


def test_unusual_is_a_warning(con, cfg):
    history(con, 1.06)
    assert dict((n, s) for n, s, _ in checks.run(con, cfg, TARGET))["unusual_moves"] == "WARN"
