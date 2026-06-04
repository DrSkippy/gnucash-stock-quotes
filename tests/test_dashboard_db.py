"""Unit tests for dashboard/db.py — config building and DB helper functions."""

import pytest
from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

import dashboard.db as _db_module


@pytest.fixture(autouse=True)
def reset_config():
    """Clear the module-level config cache between tests."""
    _db_module._config = None
    yield
    _db_module._config = None


# ---------------------------------------------------------------------------
# _build_config / get_config
# ---------------------------------------------------------------------------

class TestBuildConfig:
    def test_db_host_from_env(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "myhost")
        monkeypatch.setenv("DB_PORT", "5432")
        monkeypatch.setenv("DB_USER", "myuser")
        monkeypatch.setenv("DB_PASSWORD", "mypass")
        monkeypatch.setenv("DB_NAME", "mydb")
        c = _db_module.get_config()
        assert c["configuration"]["database"]["host"] == "myhost"

    def test_db_port_cast_to_int(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.setenv("DB_PORT", "9999")
        c = _db_module.get_config()
        assert c["configuration"]["database"]["port"] == 9999
        assert isinstance(c["configuration"]["database"]["port"], int)

    def test_default_port_5434(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.delenv("DB_PORT", raising=False)
        c = _db_module.get_config()
        assert c["configuration"]["database"]["port"] == 5434

    def test_default_db_name(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.delenv("DB_NAME", raising=False)
        c = _db_module.get_config()
        assert c["configuration"]["database"]["database"] == "stock_quotes"

    def test_stocks_parsed_from_csv(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.setenv("TICKERS_STOCKS", "AAPL,MSFT,SPY")
        monkeypatch.delenv("TICKERS_CRYPTO", raising=False)
        c = _db_module.get_config()
        assert c["tickers"]["TIME_SERIES_DAILY"] == ["AAPL", "MSFT", "SPY"]

    def test_crypto_parsed_from_csv(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.delenv("TICKERS_STOCKS", raising=False)
        monkeypatch.setenv("TICKERS_CRYPTO", "GTC,ETH,XRP")
        c = _db_module.get_config()
        assert c["tickers"]["DIGITAL_CURRENCY_DAILY"] == ["GTC", "ETH", "XRP"]

    def test_empty_tickers_become_empty_lists(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.delenv("TICKERS_STOCKS", raising=False)
        monkeypatch.delenv("TICKERS_CRYPTO", raising=False)
        c = _db_module.get_config()
        assert c["tickers"]["TIME_SERIES_DAILY"] == []
        assert c["tickers"]["DIGITAL_CURRENCY_DAILY"] == []

    def test_url_keys_match_ticker_keys(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        c = _db_module.get_config()
        assert set(c["configuration"]["url_base"].keys()) == set(c["tickers"].keys())

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.setenv("AV_API_KEY", "secret123")
        c = _db_module.get_config()
        assert c["configuration"]["key"] == "secret123"

    def test_config_cached_across_calls(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        c1 = _db_module.get_config()
        c2 = _db_module.get_config()
        assert c1 is c2

    def test_whitespace_stripped_from_tickers(self, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        monkeypatch.setenv("TICKERS_STOCKS", " AAPL , MSFT ")
        c = _db_module.get_config()
        assert c["tickers"]["TIME_SERIES_DAILY"] == ["AAPL", "MSFT"]


# ---------------------------------------------------------------------------
# get_db()
# ---------------------------------------------------------------------------

class TestGetDb:
    @patch("dashboard.db.QuoteDatabase")
    def test_yields_db_instance(self, mock_qdb_cls, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        mock_db = MagicMock()
        mock_qdb_cls.return_value = mock_db

        from dashboard.db import get_db
        with get_db() as db:
            assert db is mock_db

    @patch("dashboard.db.QuoteDatabase")
    def test_close_called_on_exit(self, mock_qdb_cls, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        mock_db = MagicMock()
        mock_qdb_cls.return_value = mock_db

        from dashboard.db import get_db
        with get_db():
            pass
        mock_db.close.assert_called_once()

    @patch("dashboard.db.QuoteDatabase")
    def test_close_called_even_on_exception(self, mock_qdb_cls, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        mock_db = MagicMock()
        mock_qdb_cls.return_value = mock_db

        from dashboard.db import get_db
        with pytest.raises(ValueError):
            with get_db():
                raise ValueError("oops")
        mock_db.close.assert_called_once()


# ---------------------------------------------------------------------------
# get_all_symbols()
# ---------------------------------------------------------------------------

class TestGetAllSymbols:
    @patch("dashboard.db.QuoteDatabase")
    def test_returns_symbol_list(self, mock_qdb_cls, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        mock_db = MagicMock()
        mock_qdb_cls.return_value = mock_db
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("AAPL",), ("MSFT",), ("SPY",)]

        from dashboard.db import get_all_symbols
        result = get_all_symbols()
        assert result == ["AAPL", "MSFT", "SPY"]
        mock_cursor.close.assert_called_once()

    @patch("dashboard.db.QuoteDatabase")
    def test_returns_empty_list_when_no_symbols(self, mock_qdb_cls, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        mock_db = MagicMock()
        mock_qdb_cls.return_value = mock_db
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        from dashboard.db import get_all_symbols
        assert get_all_symbols() == []


# ---------------------------------------------------------------------------
# get_index_meta()
# ---------------------------------------------------------------------------

class TestGetIndexMeta:
    def test_returns_dict_when_found(self):
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            "my_idx", "EQUAL_WEIGHT", date(2025, 1, 22), 10000.0
        )

        from dashboard.db import get_index_meta
        meta = get_index_meta(mock_db, "my_idx")

        assert meta["name"] == "my_idx"
        assert meta["type"] == "EQUAL_WEIGHT"
        assert meta["created_date"] == "2025-01-22"
        assert meta["portfolio_value"] == 10000.0
        mock_cursor.close.assert_called_once()

    def test_returns_empty_dict_when_not_found(self):
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        from dashboard.db import get_index_meta
        assert get_index_meta(mock_db, "nonexistent") == {}

    def test_null_portfolio_value_defaults_to_10000(self):
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("idx", "CONSTANT", date(2025, 1, 1), None)

        from dashboard.db import get_index_meta
        meta = get_index_meta(mock_db, "idx")
        assert meta["portfolio_value"] == 10_000.0


# ---------------------------------------------------------------------------
# get_last_quote_date()
# ---------------------------------------------------------------------------

class TestGetLastQuoteDate:
    @patch("dashboard.db.QuoteDatabase")
    def test_returns_date_string(self, mock_qdb_cls, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        mock_db = MagicMock()
        mock_qdb_cls.return_value = mock_db
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (date(2026, 6, 4),)

        from dashboard.db import get_last_quote_date
        assert get_last_quote_date() == "2026-06-04"

    @patch("dashboard.db.QuoteDatabase")
    def test_returns_na_when_null(self, mock_qdb_cls, monkeypatch):
        monkeypatch.setenv("DB_USER", "u")
        monkeypatch.setenv("DB_PASSWORD", "p")
        mock_db = MagicMock()
        mock_qdb_cls.return_value = mock_db
        mock_cursor = MagicMock()
        mock_db.connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (None,)

        from dashboard.db import get_last_quote_date
        assert get_last_quote_date() == "N/A"
