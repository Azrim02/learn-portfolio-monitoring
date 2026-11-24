# Project 2: Positions and valuation

Desk question: **what do I own, and what is it worth?**

```bash
./desk report                     # from the repo root
./desk report --date 2026-10-30
./desk validate                   # formula and model against official auctions
./desk save                       # store model prices in the database
```

| File | Job |
|---|---|
| `trades.csv` | Simulated trades at real prices. The only source of positions |
| `trades_full.csv` | The earlier, larger portfolio (15 holdings). Not read by the code |
| `valuation/positions.py` | Quantity, average cost, realized P&L, traded and settled cash |
| `valuation/bonds.py` | Accrued interest, yield, duration, DV01 |
| `valuation/curve.py` | Par yields to discount factors, model price |
| `valuation/portfolio.py` | Values the book and checks that NAV is fully explained |
| `manual_prices.csv` | Your own prices (for example read from FedInvest in a browser) |

## Conventions

- Bonds are quoted per 100 of face: value = quantity / 100 x clean price + accrued.
- The model price and YTM use T+1 settlement. NAV accrues interest to the valuation date.
- Yield and accrued use unadjusted coupon dates. Cash moves to the next business day on a holiday.
- Auction prices use simple interest in the first part period. YTM uses the compound market formula.
- Positions are on trade date. Settled quantity and cash are shown separately.

## Known limits

- Treasuries have model prices only. A par curve describes recent issues best.
- Dividends are booked on the ex-date, because pay dates are not in the data. No tax.
- DV01 covers Treasuries only. Bond ETFs, if held, need duration data from another source.
- Cash earns no interest. USD only.
- A bond is valued at its first settlement date until then. A later purchase that is not settled shows a small accrued difference.

## Open

- [ ] Compare model prices with FedInvest prices (manual)
