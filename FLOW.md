# How the projects fit together

The folders are layers of one system, not separate tools. The dependency goes one way: **02 depends on 01, but 01 works without 02.**

```text
Internet ──> 01-data-pipeline ──> market.duckdb ──> 02-valuation ──> ./desk report
             (get and check)      (the database)    (value)
                                                        ^
                                                        |
                                                    trades.csv
```

| Folder | Job | Question it answers |
|---|---|---|
| `01-data-pipeline` | Gets and checks market data | Can I trust the data? |
| `02-valuation` | Uses that data to value your trades | What do I own, and what is it worth? |

Project 1 does not know that you have a portfolio. Project 2 does not download anything.

## What 02 takes from 01

| Item | Used in 02 for |
|---|---|
| `data/market.duckdb` | Prices, yield curve, bond terms, dividends |
| `pipeline/db.py` | Opening and writing the database |
| `pipeline/dates.py` | Holidays and the last complete session |
| `.venv` | The installed Python packages |

## What 02 gives back

Only `./desk save` writes portfolio results to the database: the Treasury model prices. They are labelled `model`, so they do not mix with `market` prices.

## Example: one stock

1. **01** downloads the AAPL close of 349.08 and stores it.
2. **01** checks that the price is present and reasonable.
3. **02** reads `trades.csv` and finds that you own 600 shares.
4. **02** reads 349.08 from the database and calculates 600 x 349.08 = 209,448.

## Example: one Treasury

1. **01** downloads the yield curve and the bond's coupon and maturity.
2. **01** checks that every curve tenor arrived.
3. **02** reads `trades.csv` and finds a face value of 250,000.
4. **02** turns the curve into discount factors and calculates a model price of 97.797.
5. **02** adds accrued interest: 247,636 in total.

A stock uses a price from the market. A Treasury uses a price that we calculate from real market yields.

## What this means in practice

- **Run `./desk data` before `./desk report`.** Otherwise the report uses old prices. Look for a `price date` note.
- **A bad price in 01 gives a wrong value in 02.** `./desk report` does not run the checks, so read the result of `./desk data` first.
- **Do not move or rename `01-data-pipeline`.** Project 2 and `desk` look for that folder name.

## Which command uses which project

| Command | Project |
|---|---|
| `./desk data`, `./desk check` | 01 |
| `./desk report`, `./desk validate`, `./desk save` | 02, reading the 01 database |
| `./desk dashboard` | 07, reading the 01 database, with the 01 checks and the 02 values |
| `./desk test` | All |

## Where the next projects connect

Built: 01, 02 and a first version of 07. The rest is planned.

```text
01 data ──> 02 valuation ──> 03 P&L explain ────┐
   │              │                             │
   │              ├────────> 04 limits ─────────┼──> 07 dashboard
   │              │                             │    and morning note
   │              ├────────> 05 risk ───────────┤
   │              │                             │
   ├──────────────┴────────> 06 liquidity ──────┘
   │
   └── 08 reconciliation compares 02 positions with a custodian file
```

See [`PROJECTS.md`](PROJECTS.md) for the plan and [`DESK.md`](DESK.md) for the commands.
