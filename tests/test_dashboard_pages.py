"""Tests for dashboard pages and Dash app.

Imports dashboard.app first so the Dash app is created and all pages are
registered before any test runs. Callback functions are called directly
with mocked DB helpers.
"""

import os
import pytest
import pandas as pd
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from dash.exceptions import PreventUpdate

# Minimal env vars so dashboard.db doesn't raise on import
os.environ.setdefault("DB_USER", "testuser")
os.environ.setdefault("DB_PASSWORD", "testpass")

# Create the Dash app (triggers page discovery and callback registration)
import dashboard.app  # noqa: F401

# Import layout + callback functions from each page (already in sys.modules)
from dashboard.pages.index_browser import update_index_view, recalculate, _recalc_lock
from dashboard.pages.compare import update_compare
from dashboard.pages.correlations import update_correlations
from dashboard.pages.stock_browser import update_stock_chart, fetch_quotes, _fetch_lock
import dashboard.pages.index_browser as _ib
import dashboard.pages.compare as _cmp
import dashboard.pages.correlations as _corr
import dashboard.pages.stock_browser as _stk


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _mock_get_db(mock_db):
    """Return a context-manager factory that yields mock_db."""
    @contextmanager
    def _cm():
        yield mock_db
    return _cm


def _make_series(name="test_idx", n=20):
    dates = pd.date_range("2025-01-22", periods=n, freq="B")
    return pd.Series([10000.0 + i * 5 for i in range(n)], index=dates, name=name)


def _make_quotes_df(symbol="AAPL", n=20):
    dates = pd.date_range("2025-01-22", periods=n, freq="B")
    return pd.DataFrame({
        "date": dates,
        "symbol": [symbol] * n,
        "namespace": ["NASDAQ"] * n,
        "close": [150.0 + i for i in range(n)],
        "currency": ["USD"] * n,
    })


MOCK_DEFS = {
    "asset_indexes": [{
        "NAME": "test_idx",
        "TYPE": "EQUAL_WEIGHT",
        "CREATED_DATE": "2025-01-22",
        "MEMBERS": ["AAPL", "MSFT"],
    }]
}

MOCK_META = {
    "name": "test_idx",
    "type": "EQUAL_WEIGHT",
    "created_date": "2025-01-22",
    "portfolio_value": 10000.0,
}

FAKE_CONFIG = {
    "configuration": {
        "key": "testkey",
        "url_base": {
            "TIME_SERIES_DAILY": "http://fake/{}/{}",
            "DIGITAL_CURRENCY_DAILY": "http://fake/{}/{}",
        },
        "database": {
            "host": "localhost", "port": 5434,
            "user": "u", "password": "p", "database": "d",
        },
    },
    "tickers": {
        "TIME_SERIES_DAILY": ["AAPL"],
        "DIGITAL_CURRENCY_DAILY": ["GTC"],
    },
}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class TestApp:
    def test_server_is_flask_app(self):
        from flask import Flask
        assert isinstance(dashboard.app.server, Flask)

    def test_app_has_page_container(self):
        import dash
        assert dashboard.app.app.layout is not None


# ---------------------------------------------------------------------------
# Page 1 — Index Browser
# ---------------------------------------------------------------------------

class TestIndexBrowserLayout:
    def test_layout_returns_row(self):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = MOCK_DEFS

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            result = _ib.layout()

        import dash_bootstrap_components as dbc
        assert isinstance(result, dbc.Row)

    def test_layout_with_no_indexes(self):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = {"asset_indexes": []}

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            result = _ib.layout()

        import dash_bootstrap_components as dbc
        assert isinstance(result, dbc.Row)


class TestUpdateIndexView:
    def test_raises_prevent_update_when_no_index(self):
        with pytest.raises(PreventUpdate):
            update_index_view(None, None, None)

    def test_returns_figure_info_and_table(self):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = MOCK_DEFS
        mock_db.read_index_history.return_value = _make_series()
        mock_db.read_index_weights.return_value = {"AAPL": 33.33, "MSFT": 25.0}

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            with patch("dashboard.db.get_index_meta", return_value=MOCK_META):
                fig, info, table = update_index_view("test_idx", None, None)

        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1

    def test_empty_series_produces_empty_figure(self):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = {"asset_indexes": []}
        mock_db.read_index_history.return_value = pd.Series(dtype=float)
        mock_db.read_index_weights.return_value = {}

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            with patch("dashboard.db.get_index_meta", return_value={}):
                fig, info, table = update_index_view("test_idx", None, None)

        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_no_weights_returns_alert(self):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = {"asset_indexes": []}
        mock_db.read_index_history.return_value = pd.Series(dtype=float)
        mock_db.read_index_weights.return_value = {}

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            with patch("dashboard.db.get_index_meta", return_value={}):
                _, _, table = update_index_view("test_idx", None, None)

        import dash_bootstrap_components as dbc
        assert isinstance(table, dbc.Alert)

    def test_weights_present_returns_table(self):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = MOCK_DEFS
        mock_db.read_index_history.return_value = _make_series()
        mock_db.read_index_weights.return_value = {"AAPL": 10.0}

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            with patch("dashboard.db.get_index_meta", return_value=MOCK_META):
                _, _, table = update_index_view("test_idx", None, None)

        import dash_bootstrap_components as dbc
        assert isinstance(table, dbc.Table)

    def test_with_date_range(self):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = MOCK_DEFS
        mock_db.read_index_history.return_value = _make_series()
        mock_db.read_index_weights.return_value = {}

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            with patch("dashboard.db.get_index_meta", return_value=MOCK_META):
                fig, _, _ = update_index_view("test_idx", "2025-01-22", "2025-06-01")

        mock_db.read_index_history.assert_called_once_with(
            "test_idx", start_date="2025-01-22", end_date="2025-06-01"
        )


class TestRecalculate:
    def test_locked_returns_warning(self):
        _recalc_lock.acquire()
        try:
            result = recalculate(1)
        finally:
            _recalc_lock.release()
        import dash_bootstrap_components as dbc
        assert isinstance(result, dbc.Alert)
        assert result.color == "warning"

    def test_success_returns_green_alert(self):
        with patch("dashboard.db.get_config", return_value=FAKE_CONFIG):
            with patch("market_indexes.portfolio.PortfolioAnalyzer"):
                result = recalculate(1)
        import dash_bootstrap_components as dbc
        assert isinstance(result, dbc.Alert)
        assert result.color == "success"

    def test_exception_returns_danger_alert(self):
        with patch("dashboard.db.get_config", return_value=FAKE_CONFIG):
            with patch("market_indexes.portfolio.PortfolioAnalyzer",
                       side_effect=RuntimeError("db down")):
                result = recalculate(1)
        import dash_bootstrap_components as dbc
        assert result.color == "danger"


# ---------------------------------------------------------------------------
# Page 2 — Compare
# ---------------------------------------------------------------------------

class TestCompareLayout:
    def test_layout_returns_div(self):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = MOCK_DEFS

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            with patch("dashboard.db.get_all_symbols", return_value=["AAPL", "MSFT"]):
                result = _cmp.layout()

        from dash import html
        assert isinstance(result, html.Div)


class TestUpdateCompare:
    def test_raises_prevent_update_when_no_inputs(self):
        with pytest.raises(PreventUpdate):
            update_compare(None, None, 30)

    def test_returns_figure_with_data(self):
        mock_db = MagicMock()
        mock_db.read_index_history.return_value = _make_series()
        mock_db.read_quotes.return_value = _make_quotes_df("AAPL")

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            with patch("dashboard.db.get_index_meta", return_value=MOCK_META):
                fig = update_compare("test_idx", "AAPL", 30)

        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2  # index + stock + rolling corr

    def test_empty_index_history_returns_empty_figure(self):
        mock_db = MagicMock()
        mock_db.read_index_history.return_value = pd.Series(dtype=float)
        mock_db.read_quotes.return_value = _make_quotes_df("AAPL")

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            with patch("dashboard.db.get_index_meta", return_value=MOCK_META):
                fig = update_compare("test_idx", "AAPL", 30)

        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_empty_stock_quotes_returns_empty_figure(self):
        mock_db = MagicMock()
        mock_db.read_index_history.return_value = _make_series()
        mock_db.read_quotes.return_value = pd.DataFrame()

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            with patch("dashboard.db.get_index_meta", return_value=MOCK_META):
                fig = update_compare("test_idx", "AAPL", 30)

        assert len(fig.data) == 0


# ---------------------------------------------------------------------------
# Page 3 — Correlations
# ---------------------------------------------------------------------------

class TestCorrelationsLayout:
    def test_layout_returns_div(self):
        with patch("dashboard.db.get_all_symbols", return_value=["AAPL", "MSFT", "SPY"]):
            result = _corr.layout()

        from dash import html
        assert isinstance(result, html.Div)


class TestUpdateCorrelations:
    def test_raises_prevent_update_when_no_inputs(self):
        with pytest.raises(PreventUpdate):
            update_correlations(None, "MSFT", None, "time-series")

    def test_raises_prevent_update_when_sym_b_missing(self):
        with pytest.raises(PreventUpdate):
            update_correlations("AAPL", None, None, "time-series")

    def test_time_series_tab_returns_figure_and_badge(self):
        mock_db = MagicMock()
        mock_db.read_quotes.side_effect = [
            _make_quotes_df("AAPL"),
            _make_quotes_df("MSFT"),
        ]

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            fig, badge = update_correlations("AAPL", "MSFT", None, "time-series")

        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2

    def test_scatter_tab_returns_figure(self):
        mock_db = MagicMock()
        mock_db.read_quotes.side_effect = [
            _make_quotes_df("AAPL"),
            _make_quotes_df("MSFT"),
        ]

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            fig, badge = update_correlations("AAPL", "MSFT", None, "scatter")

        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Scatter)

    def test_empty_data_returns_empty_figure(self):
        mock_db = MagicMock()
        mock_db.read_quotes.side_effect = [pd.DataFrame(), pd.DataFrame()]

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            fig, badge = update_correlations("AAPL", "MSFT", None, "time-series")

        assert len(fig.data) == 0

    def test_with_start_date_filters(self):
        mock_db = MagicMock()
        mock_db.read_quotes.side_effect = [
            _make_quotes_df("AAPL"),
            _make_quotes_df("MSFT"),
        ]

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            update_correlations("AAPL", "MSFT", "2025-06-01 ", "time-series")

        calls = mock_db.read_quotes.call_args_list
        assert calls[0][1]["start_date"] == "2025-06-01"


# ---------------------------------------------------------------------------
# Page 4 — Stock Browser
# ---------------------------------------------------------------------------

class TestStockBrowserLayout:
    def test_layout_returns_div(self):
        with patch("dashboard.db.get_all_symbols", return_value=["AAPL", "MSFT", "SPY"]):
            with patch("dashboard.db.get_last_quote_date", return_value="2026-06-04"):
                result = _stk.layout()

        from dash import html
        assert isinstance(result, html.Div)


class TestUpdateStockChart:
    def test_raises_prevent_update_when_no_symbols(self):
        with pytest.raises(PreventUpdate):
            update_stock_chart(None, "norm")

    def test_raises_prevent_update_when_empty_list(self):
        with pytest.raises(PreventUpdate):
            update_stock_chart([], "norm")

    def test_normalized_chart_returns_figure(self):
        mock_db = MagicMock()
        mock_db.read_quotes.return_value = pd.concat([
            _make_quotes_df("AAPL"),
            _make_quotes_df("MSFT"),
        ])

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            fig = update_stock_chart(["AAPL", "MSFT"], "norm")

        import plotly.graph_objects as go
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2

    def test_raw_chart_returns_figure(self):
        mock_db = MagicMock()
        mock_db.read_quotes.return_value = _make_quotes_df("AAPL")

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            fig = update_stock_chart(["AAPL"], "raw")

        assert len(fig.data) == 1

    def test_caps_at_ten_symbols(self):
        symbols = [f"SYM{i}" for i in range(15)]
        mock_db = MagicMock()
        dfs = [_make_quotes_df(s) for s in symbols[:10]]
        mock_db.read_quotes.return_value = pd.concat(dfs)

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            update_stock_chart(symbols, "norm")

        called_syms = mock_db.read_quotes.call_args[1]["symbols"]
        assert len(called_syms) == 10

    def test_empty_df_returns_empty_figure(self):
        mock_db = MagicMock()
        mock_db.read_quotes.return_value = pd.DataFrame()

        with patch("dashboard.db.get_db", _mock_get_db(mock_db)):
            fig = update_stock_chart(["AAPL"], "norm")

        assert len(fig.data) == 0


class TestFetchQuotes:
    def test_locked_returns_warning(self):
        _fetch_lock.acquire()
        try:
            result = fetch_quotes(1)
        finally:
            _fetch_lock.release()
        import dash_bootstrap_components as dbc
        assert result.color == "warning"

    def test_success_returns_green_alert(self):
        mock_tq = MagicMock()
        mock_tq.fetch_quotes.return_value = [{"data": "x"}] * 3
        with patch("dashboard.db.get_config", return_value=FAKE_CONFIG):
            with patch("alphavantage.quotes.TickerQuotes", return_value=mock_tq):
                result = fetch_quotes(1)
        import dash_bootstrap_components as dbc
        assert result.color == "success"
        assert "3" in result.children

    def test_exception_returns_danger_alert(self):
        with patch("dashboard.db.get_config", return_value=FAKE_CONFIG):
            with patch("alphavantage.quotes.TickerQuotes",
                       side_effect=RuntimeError("api down")):
                result = fetch_quotes(1)
        import dash_bootstrap_components as dbc
        assert result.color == "danger"
