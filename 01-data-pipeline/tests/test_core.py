import datetime as dt

from conftest import TARGET, price
from pipeline import checks, db
from pipeline.dates import NEW_YORK, expected_date, last_complete_session
from pipeline.sources import fiscal_data, fred, tiingo, treasury_curve

D = dt.date


def test_veterans_day_bond_market_closed_stocks_open():
    assert expected_date(D(2026, 11, 11), "nyse") == D(2026, 11, 11)
    assert expected_date(D(2026, 11, 11), "bond") == D(2026, 11, 10)


def test_lag_skips_the_weekend():
    assert expected_date(TARGET, "bond", lag=1) == D(2026, 11, 20)


def test_session_is_not_complete_during_the_day():
    assert last_complete_session(dt.datetime(2026, 11, 24, 12, tzinfo=NEW_YORK)) == D(2026, 11, 23)
    assert last_complete_session(dt.datetime(2026, 11, 24, 20, tzinfo=NEW_YORK)) == D(2026, 11, 24)
    assert last_complete_session(dt.datetime(2026, 11, 26, 20, tzinfo=NEW_YORK)) == D(2026, 11, 25)


def test_rerun_makes_no_duplicates_and_keeps_loaded_at(con):
    before = con.execute("SELECT * FROM prices ORDER BY as_of").fetchall()
    db.upsert(con, "prices", [price(TARGET, 349.08)])
    assert con.execute("SELECT * FROM prices ORDER BY as_of").fetchall() == before


def test_restated_value_replaces_the_old_one(con):
    db.upsert(con, "prices", [price(TARGET, 349.10)])
    assert con.execute("SELECT price FROM prices WHERE as_of = ?", [TARGET]).fetchall() == [(349.10,)]


def test_missing_passes_on_clean_data(con, cfg):
    assert checks.missing_values(con, cfg, TARGET) == []


def test_missing_finds_price_curve_and_series(con, cfg):
    con.execute("DELETE FROM prices WHERE as_of = ?", [TARGET])
    con.execute("DELETE FROM curves WHERE as_of = ?", [TARGET])
    con.execute("DELETE FROM series")
    assert len(checks.missing_values(con, cfg, TARGET)) == 3


def test_curve_parse():
    text = 'Date,"1.5 Month","10 Yr"\n11/23/2026,4.27,4.92\n11/20/2026,,4.92\n'
    rows = treasury_curve.parse(text, "X", D(2026, 11, 20), TARGET)
    assert [(r["tenor_months"], r["par_yield"]) for r in rows] == [(1.5, 4.27), (120, 4.92), (120, 4.92)]


def test_fred_parse_skips_blank():
    rows = fred.parse("observation_date,S\n2026-11-10,4.98\n2026-11-11,\n", "S")
    assert len(rows) == 1


def test_fiscal_parse_handles_null_string_and_drops_tips():
    base = ('"cusip":"A","auction_date":"2026-10-21","issue_date":"2026-10-23",'
            '"dated_date":"2026-08-15","maturity_date":"2046-08-15","int_rate":"5.125",'
            '"high_yield":"null","price_per100":"null","reopening":"Yes","floating_rate":"No",')
    text = ('{"data":[{' + base + '"inflation_index_security":"No"},{'
            + base + '"inflation_index_security":"Yes"}]}')
    rows = fiscal_data.parse(text)
    assert len(rows) == 1 and rows[0]["price"] is None and rows[0]["coupon"] == 5.125


def test_tiingo_parse_splits_out_corporate_actions():
    text = ('[{"date":"2026-11-23T00:00:00.000Z","close":100.0,"volume":5,'
            '"divCash":0.5,"splitFactor":4.0}]')
    out = tiingo.parse(text, "AAPL", TARGET, TARGET)
    assert out["prices"][0]["price"] == 100.0
    assert {(a["kind"], a["amount"]) for a in out["corporate_actions"]} == {("dividend", 0.5), ("split", 4.0)}
