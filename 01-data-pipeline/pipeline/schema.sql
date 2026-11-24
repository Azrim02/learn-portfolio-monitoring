CREATE TABLE IF NOT EXISTS instruments (
    id TEXT PRIMARY KEY, type TEXT NOT NULL, sector TEXT, currency TEXT NOT NULL,
    coupon DOUBLE, frequency INTEGER, day_count TEXT, dated_date DATE, maturity DATE
);
CREATE TABLE IF NOT EXISTS prices (
    instrument_id TEXT, as_of DATE, source TEXT,
    price_type TEXT CHECK (price_type IN ('market', 'model', 'manual')),
    price DOUBLE NOT NULL, loaded_at TIMESTAMP NOT NULL,
    PRIMARY KEY (instrument_id, as_of, source, price_type)
);
CREATE TABLE IF NOT EXISTS volumes (
    instrument_id TEXT, as_of DATE, source TEXT, volume DOUBLE NOT NULL,
    loaded_at TIMESTAMP NOT NULL, PRIMARY KEY (instrument_id, as_of, source)
);
CREATE TABLE IF NOT EXISTS corporate_actions (
    instrument_id TEXT, ex_date DATE, kind TEXT, amount DOUBLE NOT NULL,
    loaded_at TIMESTAMP NOT NULL, PRIMARY KEY (instrument_id, ex_date, kind)
);
CREATE TABLE IF NOT EXISTS curves (
    curve_id TEXT, as_of DATE, tenor_months DOUBLE, par_yield DOUBLE NOT NULL,
    loaded_at TIMESTAMP NOT NULL, PRIMARY KEY (curve_id, as_of, tenor_months)
);
CREATE TABLE IF NOT EXISTS series (
    series_id TEXT, as_of DATE, value DOUBLE NOT NULL,
    loaded_at TIMESTAMP NOT NULL, PRIMARY KEY (series_id, as_of)
);
-- One CUSIP has several auctions when it is reopened.
CREATE TABLE IF NOT EXISTS auctions (
    cusip TEXT, auction_date DATE, issue_date DATE, dated_date DATE, maturity DATE,
    coupon DOUBLE, high_yield DOUBLE, price DOUBLE, reopening BOOLEAN,
    loaded_at TIMESTAMP NOT NULL, PRIMARY KEY (cusip, auction_date)
);
CREATE TABLE IF NOT EXISTS load_runs (
    run_at TIMESTAMP, target DATE, source TEXT, status TEXT, row_count INTEGER, message TEXT
);
CREATE TABLE IF NOT EXISTS check_results (
    run_at TIMESTAMP, target DATE, name TEXT, status TEXT, message TEXT
);
