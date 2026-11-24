# The `desk` script

`desk` is the single entry point to this repo. It runs the right Python module, in the right folder, with your API key loaded. It works from any folder.

```bash
./desk <command> [options]
```

## Daily routine

```bash
./desk data       # 1. get and check the latest data
./desk report     # 2. look at the portfolio
```

Run it after about 19:00 New York time to get that day's close. Before then, the last complete session is the previous one.

## Commands

| Command | What it does | Uses the internet | Writes |
|---|---|---|---|
| `data` | Download, store and check market data | Yes | Raw files, database |
| `check` | Run the data checks again | No | Check results |
| `report` | Show holdings, value, P&L and rate risk | No | - |
| `validate` | Compare the bond maths with official auctions | No | - |
| `save` | Store the Treasury model prices | No | Database |
| `dashboard` | Show the portfolio on a local web page | No | - |
| `test` | Run the automated tests | No | - |

| Option | Works with | Meaning |
|---|---|---|
| `--date YYYY-MM-DD` | `data`, `check`, `report`, `save` | Use this date, not the last complete session |
| `--lookback DAYS` | `data` | Calendar days to download before the date (default 10) |

---

### `./desk data`

```text
target 2026-11-23
load   OK       treasury_curve      98 rows
load   OK       tiingo             184 rows
check  PASS     missing_values
check  WARN     unusual_moves
         - SPY (tiingo): +4.71% is 5.2 standard deviations; confirm it with a second source
```

| Load status | Meaning | Action |
|---|---|---|
| `OK` | Data arrived | None |
| `EMPTY` | The source answered, but with no rows | Check the date and the source |
| `SKIPPED` | The API key is not set | Check `.env` |
| `FAILED` | The request or the storage failed | Read the message |

A failed source does not stop the others. Running it twice does not create duplicates. The row count is rows received, not rows changed.

### `./desk check`

| Check | Question | If it finds something |
|---|---|---|
| `missing_values` | Is every expected value there? | FAIL |
| `stale_prices` | Has a close not changed for 3 sessions? | FAIL |
| `outliers` | Did a price move over 15%, or a yield over 50 bp? | FAIL |
| `unusual_moves` | Is the move over 4 standard deviations for that instrument? | WARN |
| `duplicate_sources` | Do two sources disagree? | FAIL |

FAIL means do not trust the data until you understand it; a real large move can also fail. WARN means a person must look. PASS means nothing was found, not that the data is proven correct.

The checks cover every downloaded instrument, including ones you do not own.

### `./desk report`

```text
instrument  quantity     cost    price source       value  weight   unreal.    YTM  dur.   DV01
AAPL             600  330.320  349.080 market     209,448   20.9%    11,256
91282CRF0    250,000   99.541   97.797 model      247,636   24.7%    -4,358  4.912  7.63  189.0
```

| Column | Meaning |
|---|---|
| `quantity` | Shares, or face value of a bond |
| `cost` | Average purchase price, without fees or accrued interest |
| `price` | Closing price. Bonds: clean price per 100 of face |
| `source` | `market` = real closing price. `model` = calculated from the yield curve |
| `value` | Shares x price, or face / 100 x price + accrued interest |
| `weight` | Value / NAV |
| `unreal.` | Gain or loss on price if sold at this price |
| `YTM` | Yield to maturity, percent |
| `dur.` | Modified duration: approximate % price loss if yields rise 1% |
| `DV01` | USD loss if yields rise 1 bp (0.01%) |

Two notes can follow a line: `price date ...` (the price is not from the report date) and `settled ...` (a trade has not settled).

| Bottom section | Meaning |
|---|---|
| `cash, traded` | Cash after every trade |
| `cash, settled` | Cash after settled trades only |
| `NAV` | All holdings plus traded cash |
| `unrealized` / `realized` | Price gain on what you hold / on what you sold |
| `dividends`, `coupons` | Income. Dividends are booked on the ex-date |
| `net accrued` | Bond interest earned, less interest paid when buying |
| `unexplained` | Must be 0.00. If not, find the error before using the report |

### `./desk validate`

Shows each official Treasury auction next to our calculation.

| Column | Meaning | Expect |
|---|---|---|
| `official`, `formula` | Official price, and our price from the official yield | Equal to about six decimals |
| `model` | Our price from that day's yield curve | Close to official |
| `diff bp` | Model yield minus auction yield | Small; -4.8 to +6.7 bp so far |

`diff bp` is not zero because the auction and the end-of-day curve are from different times, and because the curve is an average of the market.

It also compares prices you type into `02-valuation/manual_prices.csv`:

```csv
as_of,cusip,price
2026-11-23,91282CRF0,<price you looked up>
```

### `./desk save`

Stores the Treasury model prices with `price_type = 'model'`. The report does not need this: it recalculates them.

> **Caution:** `report` and `save` do not reject a future date. They use the last known prices. Do not run `save` with a future date, because it overwrites the saved model price of the last curve date.

### `./desk dashboard`

Opens a page at http://localhost:8501 with data status, NAV, holdings and P&L by source. Press `Ctrl+C` to stop it. See `07-dashboard/README.md`.

### `./desk test`

Runs the tests of all projects. Projects 1 and 2 use sample data. The dashboard test opens the page with your database. A pass says the code works, not that today's data is good.

---

## Exit codes

| Code | `data`, `check` | Other commands |
|---|---|---|
| 0 | All good | Success |
| 1 | A load or a check failed | Error or failed test |
| 2 | Warnings to review, or a wrong option | Wrong option |

## Change the portfolio

Edit `02-valuation/trades.csv`. Positions and cash are calculated from it, starting from USD 1,000,000.

| Field | Meaning |
|---|---|
| `id` | Unique trade number |
| `side` | `BUY` or `SELL`. Selling more than you own is rejected |
| `quantity` | Shares, or face value |
| `price` | Per share, or clean price per 100 of face |
| `accrued` | Bonds: accrued interest per 100 of face. Others: 0 |
| `fees` | USD |
| `trade_date`, `settle_date` | Trade day, and the day cash and securities move |

A new instrument must be in `01-data-pipeline/config.toml` first. Then run `./desk data --lookback 400`.

## Set the API key

Create `.env` in the repo root. Never commit it.

```bash
TIINGO_API_KEY=your_key
```

```bash
chmod 600 .env
```

## Problems

| Message | Cause | Action |
|---|---|---|
| `TIINGO_API_KEY is not set` | No `.env` in the repo root | Create it |
| `429 Too Many Requests` | Tiingo rate limit. Each `data` run uses one request per stock or ETF (13 now) | Wait one hour. Stored data is safe |
| `... is not a complete session` | The date is today or in the future | Use an earlier date |
| `no instrument record` | A trade uses an instrument that is not in `config.toml` | Add it, then run `data` |
| `sells more than the position` | Wrong quantity or date in a trade | Correct `trades.csv` |
| `No such file or directory` for Python | No virtual environment | See `01-data-pipeline/README.md` |

## What is real

Market data is real and end of day. Holdings, cash and fees are simulated. Treasury prices are model values, not quotes. This is a learning tool: do not use it for trading decisions.
