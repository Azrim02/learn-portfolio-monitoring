import csv
import datetime as dt
import io

from .. import http, raw

URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
       "daily-treasury-rates.csv/{year}/all")


def tenor_months(label):
    number, unit = label.split()
    return float(number) * (12 if unit.startswith("Yr") else 1)


def parse(text, curve_id, start, end):
    rows = []
    for line in csv.DictReader(io.StringIO(text)):
        day = dt.datetime.strptime(line["Date"], "%m/%d/%Y").date()
        if not start <= day <= end:
            continue
        for label, value in line.items():
            if label != "Date" and value not in ("", "N/A", None):
                rows.append({"curve_id": curve_id, "as_of": day,
                             "tenor_months": tenor_months(label), "par_yield": float(value)})
    return rows


def fetch(cfg, start, end):
    rows = []
    for year in range(start.year, end.year + 1):
        text = http.get(URL.format(year=year), params={
            "type": "daily_treasury_yield_curve", "field_tdr_date_value": year, "_format": "csv"})
        raw.save("treasury_curve", end, f"{year}.csv", text)
        rows += parse(text, cfg["curve"]["id"], start, end)
    return {"curves": rows}
