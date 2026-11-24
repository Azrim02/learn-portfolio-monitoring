import datetime as dt

import pytest

from pipeline import db

TARGET = dt.date(2026, 11, 23)


@pytest.fixture
def cfg():
    return {
        "checks": {"stale_sessions": 3, "outlier_return": 0.15, "outlier_curve_bp": 50,
                   "unusual_sigma": 4, "unusual_window": 250, "unusual_min_history": 60,
                   "duplicate_tolerance": 0.001},
        "curve": {"id": "UST_PAR", "calendar": "bond", "lag": 0, "required_tenors": [24]},
        "series": [{"id": "SOFR", "source": "nyfed", "calendar": "bond", "lag": 1}],
        "instruments": [{"id": "AAPL", "type": "equity", "sector": "Technology"}],
    }


def price(day, value, source="tiingo"):
    return {"instrument_id": "AAPL", "as_of": day, "source": source,
            "price_type": "market", "price": value}


@pytest.fixture
def con(cfg):
    """A clean, complete small database for Mon 23 Nov 2026."""
    c = db.connect(":memory:")
    db.sync_instruments(c, cfg)
    closes = {18: 352.45, 19: 349.21, 20: 342.56, 23: 349.08}
    db.upsert(c, "prices", [price(dt.date(2026, 11, d), v) for d, v in closes.items()])
    db.upsert(c, "curves", [{"curve_id": "UST_PAR", "as_of": dt.date(2026, 11, d),
                             "tenor_months": 24.0, "par_yield": 4.63} for d in (20, 23)])
    db.upsert(c, "series", [{"series_id": "SOFR", "as_of": dt.date(2026, 11, 20), "value": 3.92}])
    yield c
    c.close()
