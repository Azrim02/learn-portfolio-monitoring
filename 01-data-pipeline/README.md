# Project 1: Data pipeline and quality checks

Desk question: **can I trust today's numbers?**

## Setup

```bash
cd 01-data-pipeline
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # already done once
# Put TIINGO_API_KEY=... in ../.env (repo root), then: chmod 600 ../.env
# Free account at tiingo.com. Never commit the key.
```

## Use

`./desk data` from the repo root loads `.env` and does the same as `run`. The direct commands below do not read `.env`; load it first with `set -a; . ../.env; set +a`.

```bash
.venv/bin/python -m pipeline run                        # load and check the last complete session
.venv/bin/python -m pipeline load --lookback 400        # backfill
.venv/bin/python -m pipeline check --date 2026-11-23
.venv/bin/python -m pytest
```

Exit code: 0 all good, 1 a load or check failed, 2 warnings to review.

## Map

| File | Job |
|---|---|
| `config.toml` | Universe, series, publication lags, thresholds |
| `pipeline/sources/` | One module per source: `fetch` and a pure `parse` |
| `pipeline/raw.py` | Write-once raw files in `data/raw/` |
| `pipeline/db.py`, `schema.sql` | DuckDB tables and safe upserts |
| `pipeline/dates.py` | Stock and bond holidays, publication lag, complete session |
| `pipeline/checks.py` | Data quality checks |

## Checks

| Check | Result if it finds something |
|---|---|
| `missing_values` | FAIL |
| `stale_prices`: close unchanged for 3 sessions | FAIL |
| `outliers`: fixed limit (15% price, 50 bp curve), split-adjusted | FAIL |
| `unusual_moves`: more than 4 standard deviations for that instrument | WARN, a person must look |
| `duplicate_sources`: two sources disagree | FAIL |

A real move can exceed the 15% limit: MSFT on 2026-07-30 and AMZN on 2026-07-31 did. Only one price source is loaded, so `duplicate_sources` has nothing to compare yet.

## Market details to know

- The bond market closes on some days when stocks trade (Veterans Day, Columbus Day).
- SOFR and OAS are published one business day later, so `lag = 1`.
- The Treasury curve is a par curve, not a zero curve.
- A reopened Treasury has several auctions with one CUSIP: key is CUSIP and auction date.
- Prices are unadjusted closes. A split looks like a crash unless you use `corporate_actions`.

## Known limits

- The OAS calendar is an assumption (`nyse`), based on one holiday.
- The database keeps the latest value after a restatement. Older values stay only in `data/raw/`.
- Treasuries have terms but no prices here. Project 2 adds model prices.
