# Project 7: Dashboard (first version)

Desk question: **what needs my attention now?**

```bash
./desk dashboard          # from the repo root, then open http://localhost:8501
```

Press `Ctrl+C` in the terminal to stop it. The page is visible only on this computer.

| Section | Use |
|---|---|
| As of | Choose any session since the first trade |
| Headline numbers | NAV and its change, P&L, DV01, settled cash |
| Data status | Runs the Project 1 checks for that date. Read it before the numbers |
| NAV / Value by holding | Hover for exact values |
| Trade history | Each purchase and sale up to the chosen date, newest first, with the cash paid or received |
| Holdings, P&L by source | The same numbers as `./desk report` |

The page only reads. It does not download data: run `./desk data`, then reload the page.

## Limits

- End of day, not live.
- The change in NAV is for the whole portfolio. Project 3 adds the cause.
- An older date uses the data stored today, so later corrections are included.
- DuckDB allows one writer: if `./desk data` is storing data, the page asks you to wait.

## Not built yet

- [ ] Daily P&L by cause (Project 3)
- [ ] Limit breaches (Project 4)
- [ ] VaR and stress tests (Project 5)
- [ ] Liquidity (Project 6)
- [ ] Morning note
