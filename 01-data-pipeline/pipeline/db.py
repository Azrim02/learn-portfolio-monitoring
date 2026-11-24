import datetime as dt

import duckdb

from . import config

KEYS = {
    "prices": ("instrument_id", "as_of", "source", "price_type"),
    "volumes": ("instrument_id", "as_of", "source"),
    "corporate_actions": ("instrument_id", "ex_date", "kind"),
    "curves": ("curve_id", "as_of", "tenor_months"),
    "series": ("series_id", "as_of"),
    "auctions": ("cusip", "auction_date"),
}


def now():
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def connect(path=None):
    if path is None:
        config.DATA.mkdir(exist_ok=True)
        path = config.DATA / "market.duckdb"
    con = duckdb.connect(str(path))
    con.execute((config.ROOT / "pipeline" / "schema.sql").read_text())
    return con


def upsert(con, table, rows):
    """Insert rows, or update them if a value changed.

    A rerun does not create duplicates. loaded_at changes only with the value.
    """
    if not rows:
        return 0
    cols = list(rows[0])
    keys = KEYS[table]
    values = [c for c in cols if c not in keys]
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}, loaded_at) "
        f"VALUES ({', '.join('?' * len(cols))}, ?) "
        f"ON CONFLICT ({', '.join(keys)}) DO UPDATE SET "
        + ", ".join(f"{c} = excluded.{c}" for c in values + ["loaded_at"])
        + " WHERE " + " OR ".join(f"{table}.{c} IS DISTINCT FROM excluded.{c}" for c in values)
    )
    stamp = now()
    con.executemany(sql, [[r[c] for c in cols] + [stamp] for r in rows])
    return len(rows)


def sync_instruments(con, cfg):
    for i in cfg["instruments"]:
        con.execute(
            "INSERT INTO instruments (id, type, sector, currency) VALUES (?, ?, ?, 'USD') "
            "ON CONFLICT (id) DO UPDATE SET type = excluded.type, sector = excluded.sector",
            [i["id"], i["type"], i["sector"]],
        )


def sync_treasury_terms(con):
    con.execute(
        """
        UPDATE instruments SET coupon = t.coupon, frequency = 2, day_count = 'ACT/ACT',
               dated_date = t.dated_date, maturity = t.maturity
        FROM (SELECT cusip, any_value(coupon) AS coupon, any_value(dated_date) AS dated_date,
                     any_value(maturity) AS maturity
              FROM auctions WHERE coupon IS NOT NULL GROUP BY cusip) AS t
        WHERE instruments.id = t.cusip AND instruments.type = 'treasury'
        """
    )
