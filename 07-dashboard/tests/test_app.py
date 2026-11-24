"""Runs the page on the real local database. Skips if there is no data."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"
DB = APP.parent.parent / "01-data-pipeline" / "data" / "market.duckdb"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="no local database")


def test_first_middle_and_last_date_render():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    options = app.selectbox[0].options
    for k in (0, len(options) // 2, len(options) - 1):
        app.selectbox[0].select_index(k).run()
        assert not app.exception
        assert app.metric[0].label == "NAV"
