# Bond and Equity Monitoring: Project List

Goal: build one monitoring system, in stages, that answers a dealer's daily questions about a mixed bond and equity portfolio using real market data. Each project adds a layer to the previous one.

Assumes proficiency in Python, SQL and Excel. The focus is on the market and desk knowledge.

## Data sources

Tested from this machine on 2026-11-24 unless marked otherwise.

| Need | Source | Status and cautions |
|---|---|---|
| Equity and ETF prices, volume | Tiingo end-of-day API | Not tested live: needs a free key. Check its current limits and license. |
| - | `yfinance` (Yahoo) | Responds, but not used: robots.txt on Yahoo's data hosts disallows automated clients. |
| Treasury par yield curve | Treasury.gov daily CSV | Works, no key. Par yields, so bootstrap before discounting individual cash flows. |
| Treasury terms (CUSIP, coupon, dates, auction price) | Fiscal Data API, `auctions_query` | Works, no key. Missing values arrive as the string `"null"`. On 2026-11-24 the newest auction was 2026-10-22, so treat it as a source of terms, not of current auctions. |
| SOFR | New York Fed Markets API | Works, no key. |
| Yield and credit spread history | FRED (`DGS10`, `BAMLC0A0CM`) | CSV works with the default client and robots.txt allows it (1 second between requests). An official API with a free key also exists. Check history length and series terms. |
| Euro area curve | ECB Data API | Works, no key. Only needed for euro bonds. |
| Credit exposure proxy | `LQD`, `HYG` ETFs | Prices from Tiingo, not tested live. |
| Individual corporate bonds | FINRA fixed income data | Not tested. Free for non-commercial use; automated access needs an agreement or account. Look up manually at first. |
| Treasury prices by CUSIP | TreasuryDirect FedInvest | Manual browser use only: robots.txt disallows general automated clients. |
| Stooq | - | Do not use: blocks scripts with a browser check. |

### Two data rules

1. Store every price with `price_type` (`market`, `model` or `manual`), source, as-of date and load time. Never mix types silently.
2. Keep raw downloads unchanged. Derive everything else so that any past report can be rebuilt.

## Starter portfolio

Simulated holdings, real prices. Record as trades, not as a table of positions.

- 8-10 equities across at least 5 sectors
- 4 Treasuries, at about 2, 5, 10 and 30 years
- `LQD` and `HYG` for credit
- Cash in USD

Suggested benchmark: 60% `SPY`, 40% `AGG`. Use total return (include dividends and coupons).

## Architecture

```text
APIs -> raw files -> DuckDB -> valuation -> risk and limits -> dashboard
                        ^                                   -> alerts
              trades and instruments                        -> morning note
```

Stack: pandas, DuckDB, QuantLib, Streamlit. Scheduled with cron or a systemd timer. The stack installs on Python 3.15.2.

| Table | Grain | Key fields |
|---|---|---|
| `instruments` | instrument | id, type, currency, sector, coupon, frequency, day count, maturity |
| `trades` | trade | id, instrument, side, quantity, price, accrued, fees, trade and settle dates |
| `prices` | instrument, date, source | clean price, price_type, as_of, loaded_at |
| `volumes` | instrument, date | volume |
| `curves` | curve, date, tenor | par yield |
| `series` | series, date | SOFR and OAS values |
| `cash_flows` | instrument, pay date | coupon, principal, dividend |
| `limits` | limit | metric, scope, warning level, hard level |
| `alerts` | event | limit, value, time, status, comment |

---

## Project 1: Data pipeline and quality checks

Scaffold: [`01-data-pipeline/`](01-data-pipeline/README.md)

**Desk question:** Can I trust today's numbers?

- Load prices, volumes, curves and security terms into DuckDB.
- Make reruns safe: the same date must not create duplicates.
- Check for missing, stale, duplicate and outlier values. Handle market holidays.

**Done when:** one command loads a day, and a deliberately corrupted price is caught.

## Project 2: Positions and valuation

**Desk question:** What do I own, and what is it worth?

- Build positions and cash from trades, on trade date and settlement date.
- Equity: market value, corporate actions, dividends.
- Bond: clean price, accrued interest, dirty price, yield to maturity.
- Bootstrap the par curve and produce a `model` price for each Treasury.

**Done when:**

- Formula prices match official auction prices. Already proven: 16 of 16 new 2, 3, 5 and 7-year notes matched to six decimals.
- Model prices are compared with manually obtained FedInvest prices, and the differences are explained.

The auction test proves the yield-to-price formula on the issue date only. It does not prove accrued interest or curve bootstrapping, so test those separately.

## Project 3: P&L and P&L explain

**Desk question:** What did I make, and why?

| Equity | Bond |
|---|---|
| Price move | Carry and coupon |
| Dividend | Roll-down |
| FX | Curve move (`-DV01 x change in bp`, plus convexity) |
| Fees | Spread move, fees |

- Report daily, month-to-date and year-to-date.
- Show the unexplained residual. Never hide it.

**Done when:** components plus residual equal total P&L every day.

## Project 4: Exposure, limits and alerts

**Desk question:** Am I inside my mandate?

| Limit | Warning | Hard |
|---|---|---|
| Single equity weight | 8% | 10% |
| Equity sector weight | 25% | 30% |
| Portfolio modified duration | 5.5 | 6.0 |
| Total DV01 per USD 1m NAV | 450 | 500 |
| High yield weight | 8% | 10% |
| Minimum cash | 3% | 2% |
| Price age, trading days | 1 | 2 |

These levels are learning defaults, not industry standards. Set them from your own mandate.

- Show key rate DV01 by curve bucket, not only total DV01.
- Record every breach with an explanation and resolution.

**Done when:** each limit has a test just inside and just outside its level.

## Project 5: Risk and stress tests

**Desk question:** How much can I lose?

- Equity volatility, beta and drawdown; bond duration, convexity and DV01.
- Historical simulation 95% and 99% VaR and expected shortfall. Apply equity returns and curve moves **from the same dates** to keep their correlation.
- Stress: curve +100 bp, steepener, flattener, equities -20%, spreads +200 bp, and stocks and bonds falling together.
- Backtest: count days when the loss exceeded VaR.

**Done when:** a small shock matches DV01, and the exceptions are reviewed against the expected count.

## Project 6: Liquidity and execution quality

**Desk question:** Did I trade well, and how quickly can I exit?

- Equity: days to liquidate at 10-20% of ADV, arrival slippage, VWAP comparison.
- Bond: compare simulated quotes with a reference price. Treat size and bid-ask as assumptions, because free quotes are limited.
- Simulate a three-dealer request for quote: record cover, spread and hit rate.

**Done when:** an execution report explains the cost of each order in bp and USD.

## Project 7: Dashboard and morning note

**Desk question:** What needs my attention now?

Dashboard order: data status, breaches, P&L, exposure, risk, liquidity.

Write one page daily: overnight moves, effect on this portfolio, changed risk, today's events, actions.

**Done when:** the dashboard shows the as-of time and price type, and 20 consecutive trading days have a note.

## Project 8: Reconciliation

**Desk question:** Do my records match the custodian's?

- Create a custodian file with planted quantity, price, accrued interest, settlement and missing-trade errors.
- Match, classify, assign and age each break.

**Done when:** every planted error is found with no false matches.

---

## Suggested schedule

| Week | Work |
|---|---|
| 1 | Project 1 |
| 2 | Project 2 |
| 3 | Project 3 |
| 4 | Project 4 |
| 5 | Project 5 |
| 6 | Project 6 |
| 7 | Project 7, first version |
| 8 | Project 8 and write-up |

Start the morning note by hand in week 1.

## Limits of this system

- End of day, not live. Suitable for learning monitoring, not for trading decisions.
- Treasury values based on the curve are model prices, not executable quotes.
- Credit is represented by ETFs, which do not behave exactly like individual bonds.
- Executions are simulated and understate real market impact.

## Progress

- [ ] 1 Data pipeline
- [ ] 2 Valuation
- [ ] 3 P&L explain
- [ ] 4 Limits and alerts
- [ ] 5 Risk and stress
- [ ] 6 Liquidity and execution
- [ ] 7 Dashboard and morning note
- [ ] 8 Reconciliation
