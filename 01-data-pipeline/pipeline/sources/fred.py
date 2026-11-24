import csv
import datetime as dt
import io

from .. import http, raw

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def parse(text, series_id):
    return [{"series_id": series_id, "as_of": dt.date.fromisoformat(x["observation_date"]),
             "value": float(x[series_id])}
            for x in csv.DictReader(io.StringIO(text)) if x[series_id] not in ("", ".")]


def fetch(cfg, start, end):
    rows = []
    for s in cfg["series"]:
        if s["source"] != "fred":
            continue
        text = http.get(URL, params={"id": s["id"], "cosd": start.isoformat(),
                                     "coed": end.isoformat()})
        raw.save("fred", end, f"{s['id']}.csv", text)
        rows += parse(text, s["id"])
    return {"series": rows}
