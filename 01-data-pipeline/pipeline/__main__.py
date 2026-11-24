"""python -m pipeline run|load|check [--date YYYY-MM-DD] [--lookback DAYS]

Exit code: 0 all good, 1 a load or a check failed, 2 warnings to review.
"""
import argparse
import datetime as dt
import sys

from . import checks, config, db
from .dates import last_complete_session
from .sources import Skipped, fiscal_data, fred, nyfed, tiingo, treasury_curve

SOURCES = {"treasury_curve": treasury_curve, "fiscal_data": fiscal_data,
           "nyfed": nyfed, "fred": fred, "tiingo": tiingo}


def load(con, cfg, target, lookback):
    start = target - dt.timedelta(days=lookback)
    failed = False
    db.sync_instruments(con, cfg)
    for name, source in SOURCES.items():
        count, message = 0, ""
        try:
            tables = source.fetch(cfg, start, target)
            con.begin()
            try:
                count = sum(db.upsert(con, t, rows) for t, rows in tables.items())
                con.commit()
            except Exception:
                con.rollback()
                raise
            status = "OK" if count else "EMPTY"
        except Skipped as e:
            status, message = "SKIPPED", str(e)
        except Exception as e:   # one bad source must not stop the others
            status, message = "FAILED", f"{type(e).__name__}: {e}"
        failed |= status != "OK"
        con.execute("INSERT INTO load_runs VALUES (?, ?, ?, ?, ?, ?)",
                    [db.now(), target, name, status, count, message])
        print(f"load   {status:8} {name:16} {count:5} rows  {message}")
    db.sync_treasury_terms(con)
    return 1 if failed else 0


def check(con, cfg, target):
    statuses = set()
    for name, status, problems in checks.run(con, cfg, target):
        statuses.add(status)
        con.execute("INSERT INTO check_results VALUES (?, ?, ?, ?, ?)",
                    [db.now(), target, name, status, "; ".join(problems)])
        print(f"check  {status:8} {name}")
        for p in problems:
            print(f"         - {p}")
    return 1 if "FAIL" in statuses else 2 if "WARN" in statuses else 0


def main():
    p = argparse.ArgumentParser(prog="pipeline")
    p.add_argument("command", choices=["run", "load", "check"])
    p.add_argument("--date", type=dt.date.fromisoformat, help="default: last complete session")
    p.add_argument("--lookback", type=int)
    a = p.parse_args()
    cfg = config.load()
    target = a.date or last_complete_session()
    if target > last_complete_session():
        p.error(f"{target} is not a complete session")
    lookback = cfg["settings"]["lookback_days"] if a.lookback is None else a.lookback
    con = db.connect()
    print(f"target {target}")
    code = 0
    if a.command in ("run", "load"):
        code = load(con, cfg, target, lookback)
    if a.command in ("run", "check"):
        checked = check(con, cfg, target)
        code = 1 if 1 in (code, checked) else checked
    con.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
