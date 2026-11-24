"""python -m valuation report|validate|save [--date YYYY-MM-DD]"""
import argparse
import csv
import datetime as dt

from . import ROOT, bonds, curve as curves, portfolio, positions
from pipeline import db
from pipeline.dates import last_complete_session


def report(con, trades, as_of):
    v = portfolio.value(con, trades, as_of)
    print(f"Portfolio at {as_of}   curve {v['curve_date']}   simulated holdings, USD\n")
    print(f"{'instrument':11}{'quantity':>9}{'cost':>9}{'price':>9} {'source':7}{'value':>11}"
          f"{'weight':>8}{'unreal.':>10}{'YTM':>7}{'dur.':>6}{'DV01':>7}")
    for kind in ("equity", "etf", "treasury"):
        group = [r for r in v["rows"] if r["type"] == kind]
        if not group:
            continue
        for r in group:
            stale = "" if r["price_date"] == as_of else f"  price date {r['price_date']}"
            risk = (f"{r['ytm']:7.3f}{r['duration']:6.2f}{r['dv01']:7.1f}" if r["ytm"] else "")
            open_ = "" if r["settled"] == r["quantity"] else f"  settled {r['settled']:g}"
            print(f"{r['id']:11}{r['quantity']:9,.0f}{r['avg_cost']:9.3f}{r['price']:9.3f} "
                  f"{r['price_type']:7}{r['value']:11,.0f}{r['weight']:8.1%}{r['unrealized']:10,.0f}"
                  f"{risk}{stale}{open_}")
        print(f"{'  ' + kind:46}{sum(r['value'] for r in group):11,.0f}"
              f"{sum(r['weight'] for r in group):8.1%}{sum(r['unrealized'] for r in group):10,.0f}\n")
    c = v["cash"]
    print(f"{'  cash, traded':46}{c['traded']:11,.0f}{c['traded'] / v['nav']:8.1%}")
    print(f"{'  cash, settled':46}{c['settled']:11,.0f}")
    print(f"{'  NAV':46}{v['nav']:11,.0f}\n")
    print("P&L since start")
    for name, x in (("unrealized", sum(r["unrealized"] for r in v["rows"])),
                    ("realized", v["realized"]), ("dividends (ex-date)", v["income"]["dividend"]),
                    ("coupons", v["income"]["coupon"]),
                    ("net accrued", sum(r["accrued"] for r in v["rows"]) + v["income"]["accrued_paid"]),
                    ("fees", v["income"]["fees"])):
        print(f"  {name:22}{x:11,.0f}")
    print(f"  {'total':22}{v['nav'] - positions.START_CASH:11,.0f}")
    print(f"  {'unexplained':22}{portfolio.identity_gap(v):11.2f}")
    etfs = [r["id"] for r in v["rows"] if r["type"] == "etf"]
    print(f"\nDV01 {v['dv01']:,.0f} USD per bp, Treasuries only."
          + (f" Not included: {', '.join(etfs)}; bond ETFs also have rate risk." if etfs else ""))
    print("Treasury prices are model prices from the par curve, not quotes.")


def validate(con, trades, as_of):
    """Model yields against official auction results, and manual prices if you have them."""
    print("Auctions: accrued and price use the official yield; model uses that day's par curve\n")
    print(f"{'cusip':11}{'auction':12}{'official':>11}{'formula':>11}{'model':>10}"
          f"{'auction y':>10}{'model y':>9}{'diff bp':>9}")
    for cusip, auction, issue, y, price in con.execute(
            "SELECT cusip, auction_date, issue_date, high_yield, price FROM auctions "
            "WHERE price IS NOT NULL AND high_yield IS NOT NULL ORDER BY auction_date").fetchall():
        b = portfolio.treasury(con, cusip)
        model = curves.model_clean_price(curves.load(con, auction), b, issue)
        model_y = bonds.yield_from_price(b, model, issue)
        print(f"{cusip:11}{auction!s:12}{price:11.6f}{bonds.auction_price(b, y, issue):11.6f}"
              f"{model:10.4f}{y:10.3f}{model_y:9.3f}{(model_y - y) * 100:9.1f}")
    path = ROOT / "manual_prices.csv"
    rows = list(csv.DictReader(open(path, newline=""))) if path.exists() else []
    print(f"\nManual prices in {path.name}: {len(rows)}")
    for r in rows:
        day, b = dt.date.fromisoformat(r["as_of"]), portfolio.treasury(con, r["cusip"])
        settle = bonds.settlement(day)
        model = curves.model_clean_price(curves.load(con, day), b, settle)
        gap = bonds.yield_from_price(b, model, settle) - bonds.yield_from_price(b, float(r["price"]), settle)
        print(f"{r['cusip']:11}{day!s:12} manual {float(r['price']):9.4f} model {model:9.4f} "
              f"model yield {gap * 100:+.1f} bp")


def save(con, trades, as_of):
    v = portfolio.value(con, trades, as_of)
    rows = [{"instrument_id": r["id"], "as_of": r["price_date"], "source": "par_curve",
             "price_type": "model", "price": r["price"]}
            for r in v["rows"] if r["price_type"] == "model"]
    print(f"saved {db.upsert(con, 'prices', rows)} model prices")


def main():
    p = argparse.ArgumentParser(prog="valuation")
    p.add_argument("command", choices=["report", "validate", "save"])
    p.add_argument("--date", type=dt.date.fromisoformat)
    a = p.parse_args()
    con = db.connect()
    trades = positions.read_trades(ROOT / "trades.csv")
    globals()[a.command](con, trades, a.date or last_complete_session())
    con.close()


main()
