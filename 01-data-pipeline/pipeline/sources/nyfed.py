import datetime as dt
import json

from .. import http, raw

URL = "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json"


def parse(text):
    return [{"series_id": x["type"], "as_of": dt.date.fromisoformat(x["effectiveDate"]),
             "value": float(x["percentRate"])} for x in json.loads(text)["refRates"]]


def fetch(cfg, start, end):
    text = http.get(URL, params={"startDate": start.isoformat(), "endDate": end.isoformat()})
    raw.save("nyfed", end, "sofr.json", text)
    return {"series": parse(text)}
