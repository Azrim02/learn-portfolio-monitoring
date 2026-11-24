"""Project 7, first version: one page with data status, NAV and holdings.

Read only. It uses Project 1 for the checks and Project 2 for the values.
"""
import sys
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "02-valuation"))

import valuation  # noqa: E402  (adds Project 1 to the path)
from valuation import portfolio, positions  # noqa: E402
from pipeline import checks, config  # noqa: E402

DB = config.DATA / "market.duckdb"
TRADES = REPO / "02-valuation" / "trades.csv"
NAMES = {"91282CRP8": "UST 2Y 4.750% 2028", "91282CRN3": "UST 5Y 5.000% 2031",
         "91282CRF0": "UST 10Y 4.625% 2036", "912810UW6": "UST 30Y 5.125% 2056"}

st.set_page_config(page_title="Portfolio monitor", layout="wide")


@st.cache_data
def load(versions):
    """All sessions since the first trade. versions: file times, so new data reloads."""
    con = duckdb.connect(str(DB), read_only=True)
    try:
        trades = positions.read_trades(TRADES)
        days = [r[0] for r in con.execute(
            "SELECT DISTINCT as_of FROM prices WHERE price_type = 'market' AND as_of >= ? ORDER BY 1",
            [trades[0]["trade_date"]]).fetchall()]
        return {d: portfolio.value(con, trades, d) for d in days}
    finally:
        con.close()


@st.cache_data
def data_checks(versions, day):
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return checks.run(con, config.load(), day)
    finally:
        con.close()


try:
    files = (DB, TRADES, config.ROOT / "config.toml")
    versions = tuple(f.stat().st_mtime_ns for f in files)
    history = load(versions)
except FileNotFoundError as e:
    st.error(f"File not found: {e.filename}. Run ./desk data first.")
    st.stop()
except duckdb.IOException:
    st.error("The database is in use by another command. Wait for it to finish, then reload the page.")
    st.stop()
if not history:
    st.error("No market prices since the first trade. Run ./desk data --lookback 400.")
    st.stop()

days = list(history)
accent = "#3987e5" if st.context.theme.type == "dark" else "#2a78d6"

left, right = st.columns([3, 1], vertical_alignment="bottom")
left.title("Portfolio monitor")
day = right.selectbox("As of", days[::-1], format_func=lambda d: f"{d:%a %d %b %Y}")
v = history[day]
i = days.index(day)
before = history[days[i - 1]] if i else None
left.caption(f"Yield curve {v['curve_date']:%d %b %Y}. Real market data, end of day. Simulated holdings, USD.")

# ---- headline numbers
day_pnl = v["nav"] - before["nav"] if before else None
tiles = st.columns(4)
tiles[0].metric("NAV", f"{v['nav']:,.0f}", border=True, height="stretch",
                delta=f"{day_pnl:+,.0f} since {days[i - 1]:%d %b}" if before else None)
tiles[1].metric("P&L since start", f"{v['nav'] - positions.START_CASH:+,.0f}", border=True, height="stretch")
tiles[2].metric("Treasury DV01", f"{v['dv01']:,.0f}", border=True, height="stretch",
                help="USD loss if yields rise by 1 bp (0.01%). Bond ETFs are not included.")
tiles[3].metric("Settled cash", f"{v['cash']['settled']:,.0f}", border=True, height="stretch")

# ---- can I trust it?
st.subheader("Data status")
results = data_checks(versions, day)
gap = portfolio.identity_gap(v)
problems = [(n, s, p) for n, s, p in results if s != "PASS"]
if abs(gap) > 0.01:
    st.error(f"NAV is not fully explained: {gap:,.2f}. Do not use this page.", icon=":material/error:")
old = [r["id"] for r in v["rows"] if r["price_date"] != day]
if old:
    st.info(f"Price from an earlier date: {', '.join(old)}", icon=":material/schedule:")
for name, status, found in problems:
    box, icon = ((st.error, ":material/error:") if status == "FAIL" else (st.warning, ":material/warning:"))
    box(f"**{status} {name}**: " + "; ".join(found), icon=icon)
passed = [n for n, s, _ in results if s == "PASS"]
st.caption(f"{len(passed)} of {len(results)} checks passed: {', '.join(passed) or 'none'}. "
           "Checks cover every downloaded instrument, including ones you do not own.")

# ---- charts
nav = pd.DataFrame({"date": pd.to_datetime(days[:i + 1]),
                    "NAV": [history[d]["nav"] for d in days[:i + 1]]})
hold = pd.DataFrame([{"holding": NAMES.get(r["id"], r["id"]), "value": r["value"], "weight": r["weight"]}
                     for r in v["rows"]]
                    + [{"holding": "Cash", "value": v["cash"]["traded"],
                        "weight": v["cash"]["traded"] / v["nav"]}]).sort_values("value", ascending=False)

a, b = st.columns(2)
with a:
    st.subheader("NAV since the first trade")
    x = alt.X("date:T", title=None, axis=alt.Axis(format="%d %b", grid=False, tickCount=6))
    y = alt.Y("NAV:Q", title="USD", scale=alt.Scale(zero=False, nice=True),
              axis=alt.Axis(format="~s", tickCount=5))
    tip = [alt.Tooltip("date:T", title="Date", format="%d %b %Y"),
           alt.Tooltip("NAV:Q", title="NAV (USD)", format=",.0f")]
    near = alt.selection_point(nearest=True, on="pointerover", encodings=["x"], empty=False)
    base = alt.Chart(nav).encode(x=x, y=y)
    st.altair_chart(alt.layer(
        base.mark_line(color=accent, strokeWidth=2, strokeCap="round", strokeJoin="round"),
        alt.Chart(nav).mark_rule(color="#888", strokeWidth=1).encode(
            x=x, opacity=alt.condition(near, alt.value(0.6), alt.value(0))),
        base.mark_circle(color=accent, size=80, opacity=1).encode(
            opacity=alt.condition(near, alt.value(1), alt.value(0))),
        base.mark_circle(size=400, opacity=0).encode(tooltip=tip).add_params(near),
    ).properties(height=260), width="stretch")
    st.caption("The axis does not start at zero. The portfolio starts with 1,000,000 in cash.")
with b:
    st.subheader("Value by holding")
    hb = alt.Chart(hold).encode(
        y=alt.Y("holding:N", sort=None, title=None, axis=alt.Axis(labelLimit=200, ticks=False, domain=False)),
        x=alt.X("value:Q", title=None, axis=None, scale=alt.Scale(domain=[0, hold["value"].max() * 1.25])),
        tooltip=[alt.Tooltip("holding:N", title="Holding"),
                 alt.Tooltip("value:Q", title="Value (USD)", format=",.0f"),
                 alt.Tooltip("weight:Q", title="Weight", format=".1%")])
    text_color = "#c3c2b7" if st.context.theme.type == "dark" else "#52514e"
    st.altair_chart(alt.layer(
        hb.mark_bar(color=accent, size=20, cornerRadiusEnd=4),
        hb.mark_text(align="left", dx=6, color=text_color).encode(text=alt.Text("weight:Q", format=".1%")),
    ).properties(height=260), width="stretch")
    st.caption("Labels show the share of NAV.")

# ---- tables
st.subheader("Holdings")
table = pd.DataFrame([{
    "Holding": NAMES.get(r["id"], r["id"]), "ID": r["id"], "Quantity": r["quantity"],
    "Cost": r["avg_cost"], "Price": r["price"], "Price type": r["price_type"], "Value": r["value"],
    "Weight": r["weight"] * 100, "Unrealized": r["unrealized"], "Settled": r["settled"],
    "YTM": r["ytm"], "Duration": r["duration"], "DV01": r["dv01"]} for r in v["rows"]])
if table.empty:
    st.write("No holdings on this date.")
else:
    n = st.column_config.NumberColumn
    st.dataframe(table, hide_index=True, width="stretch", placeholder="-", column_config={
        "Quantity": n(format="localized"), "Settled": n(format="localized"),
        "Cost": n(format="%.3f"), "Price": n(format="%.3f"), "Value": n(format="%,.0f"),
        "Weight": n(format="%.1f%%"), "Unrealized": n(format="%+,.0f"), "YTM": n(format="%.3f%%"),
        "Duration": n(format="%.2f"), "DV01": n(format="%.1f")})
st.caption("Treasury prices are model prices from the par curve, not quotes. "
           "Bond quantity is face value; bond price is per 100 of face.")

st.subheader("P&L since start, by source")
income = v["income"]
st.dataframe(pd.DataFrame([
    ("Unrealized", sum(r["unrealized"] for r in v["rows"])),
    ("Realized", v["realized"]),
    ("Dividends (ex-date)", income["dividend"]),
    ("Coupons", income["coupon"]),
    ("Net accrued interest", sum(r["accrued"] for r in v["rows"]) + income["accrued_paid"]),
    ("Fees", income["fees"]),
    ("Total", v["nav"] - positions.START_CASH),
], columns=["Source", "USD"]), hide_index=True, width="content",
    column_config={"USD": st.column_config.NumberColumn(format="%+,.0f")})
