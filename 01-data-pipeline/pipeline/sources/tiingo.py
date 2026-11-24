"""Equity and ETF prices. Needs a free key in TIINGO_API_KEY.

Stores the unadjusted close. Dividends and splits go to corporate_actions.
"""
import datetime as dt
import json
import os

from .. import config, http, raw
from . import Skipped

URL = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"


def parse(text, ticker, start, end):
    out = {"prices": [], "volumes": [], "corporate_actions": []}
    for x in json.loads(text):
        day = dt.date.fromisoformat(x["date"][:10])
        if not start <= day <= end:
            continue
        out["prices"].append({"instrument_id": ticker, "as_of": day, "source": "tiingo",
                              "price_type": "market", "price": float(x["close"])})
        out["volumes"].append({"instrument_id": ticker, "as_of": day, "source": "tiingo",
                               "volume": float(x["volume"])})
        for field, kind, neutral in (("divCash", "dividend", 0), ("splitFactor", "split", 1)):
            if x[field] != neutral:
                out["corporate_actions"].append({"instrument_id": ticker, "ex_date": day,
                                                 "kind": kind, "amount": float(x[field])})
    return out


def fetch(cfg, start, end):
    key = os.environ.get("TIINGO_API_KEY")
    if not key:
        raise Skipped("TIINGO_API_KEY is not set")
    out = {"prices": [], "volumes": [], "corporate_actions": []}
    for ticker in config.market_priced(cfg):
        text = http.get(URL.format(ticker=ticker),
                        params={"startDate": start.isoformat(), "endDate": end.isoformat()},
                        headers={"Authorization": f"Token {key}"})
        raw.save("tiingo", end, f"{ticker}.json", text)
        for table, rows in parse(text, ticker, start, end).items():
            out[table] += rows
    return out
