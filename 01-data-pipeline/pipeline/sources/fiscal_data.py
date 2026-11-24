import datetime as dt
import json

from .. import http, raw

URL = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
       "v1/accounting/od/auctions_query")


def _value(text):
    return None if text in (None, "", "null") else text   # the API sends "null" as a string


def _number(text):
    return None if _value(text) is None else float(text)


def parse(text):
    rows = []
    for x in json.loads(text)["data"]:
        if x["inflation_index_security"] == "Yes" or x["floating_rate"] == "Yes":
            continue   # fixed-coupon securities only
        date = lambda k: dt.date.fromisoformat(x[k]) if _value(x[k]) else None
        rows.append({
            "cusip": x["cusip"], "auction_date": date("auction_date"),
            "issue_date": date("issue_date"), "dated_date": date("dated_date"),
            "maturity": date("maturity_date"), "coupon": _number(x["int_rate"]),
            "high_yield": _number(x["high_yield"]), "price": _number(x["price_per100"]),
            "reopening": x["reopening"] == "Yes",
        })
    return rows


def fetch(cfg, start, end):
    cusips = [i["id"] for i in cfg["instruments"] if i["type"] == "treasury"]
    text = http.get(URL, params={
        "filter": f"cusip:in:({','.join(cusips)})",   # all dates: terms do not change
        "page[size]": 200})
    raw.save("fiscal_data", end, "auctions.json", text)
    return {"auctions": parse(text)}
