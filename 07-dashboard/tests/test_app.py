"""Runs the page on the real local database. Skips if there is no data."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"
DB = APP.parent.parent / "01-data-pipeline" / "data" / "market.duckdb"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="no local database")


def test_first_middle_and_last_date_render():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    options = app.selectbox[0].options
    for k in (0, len(options) // 2, len(options) - 1):
        app.selectbox[0].select_index(k).run()
        assert not app.exception
        assert app.metric[0].label == "NAV"
        assert not app.error


def test_trade_history_explains_the_cash():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    trades = next(d.value for d in app.dataframe if "Trade date" in d.value.columns)
    pnl = next(d.value for d in app.dataframe if "Source" in d.value.columns).set_index("Source")["USD"]
    cash = 1_000_000 + trades["Cash"].sum() + pnl["Dividends (ex-date)"] + pnl["Coupons"]
    if (trades["Status"] == "Settled").all():
        assert f"{cash:,.0f}" == next(m.value for m in app.metric if m.label == "Settled cash")
