# Project 1: Data pipeline and quality checks

Desk question: **can I trust today's numbers?**

## Setup

```bash
cd 01-data-pipeline
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # already done once
export TIINGO_API_KEY=...        # free account at tiingo.com; never commit it
```

## Use

```bash
.venv/bin/python -m pipeline run                        # load and check the last complete session
.venv/bin/python -m pipeline load --lookback 400        # backfill
.venv/bin/python -m pipeline check --date 2026-11-23
.venv/bin/python -m pytest
```

Exit code: 0 all good, 1 a load or check failed, 2 only TODO checks remain.

## Map

| File | Job |
|---|---|
| `config.toml` | Universe, series, publication lags, thresholds |
| `pipeline/sources/` | One module per source: `fetch` and a pure `parse` |
| `pipeline/raw.py` | Write-once raw files in `data/raw/` |
| `pipeline/db.py`, `schema.sql` | DuckDB tables and safe upserts |
| `pipeline/dates.py` | Stock and bond holidays, publication lag, complete session |
| `pipeline/checks.py` | **Your work** |
| `tests/test_todo_checks.py` | **Your targets** |

## Your work

`missing_values` is complete and is your example. Write, in this order:

1. `stale_prices`
2. `outliers`
3. `duplicate_sources`

Remove the `@todo` mark from its tests as you write each check. An unwritten check reports TODO, never PASS. The tests are a minimum: add cases of your own.

## Done when

- [ ] `run` loads every source with a Tiingo key set
- [ ] `missing_values` passes on real data
- [ ] No TODO remains, and all tests pass without the `@todo` mark
- [ ] The corrupted price test (`349.08` -> `3490.80`) is caught

## Market details to know

- The bond market closes on some days when stocks trade (Veterans Day, Columbus Day).
- SOFR and OAS are published one business day later, so `lag = 1`.
- The Treasury curve is a par curve, not a zero curve.
- A reopened Treasury has several auctions with one CUSIP: key is CUSIP and auction date.
- Prices are unadjusted closes. A split looks like a crash unless you use `corporate_actions`.

## Known limits

- The Tiingo loader is tested only with sample data until a key is set.
- The OAS calendar is an assumption (`nyse`), based on one holiday.
- The database keeps the latest value after a restatement. Older values stay only in `data/raw/`.
- Treasuries have terms but no prices here. Project 2 adds model prices.
