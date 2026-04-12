"""
Unit tests for alphavantage/db_utils.py.

All tests mock psycopg2 so no real database is required.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import pandas as pd
import numpy as np
from datetime import date
import psycopg2 as _psycopg2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DB_CONFIG = {
    "configuration": {
        "database": {
            "host": "localhost",
            "port": 5434,
            "user": "scott",
            "password": "secret",
            "database": "stock_quotes",
        }
    }
}


def make_db(mock_psycopg2):
    """Return a QuoteDatabase wired to the given mock."""
    mock_conn = MagicMock()
    mock_conn.closed = 0
    mock_psycopg2.connect.return_value = mock_conn
    from alphavantage.db_utils import QuoteDatabase
    db = QuoteDatabase(DB_CONFIG)
    return db, mock_conn


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------

class TestConnect:
    @patch("alphavantage.db_utils.psycopg2")
    def test_connect_calls_psycopg2(self, mock_psycopg2):
        mock_conn = MagicMock()
        mock_conn.closed = 0
        mock_psycopg2.connect.return_value = mock_conn

        from alphavantage.db_utils import QuoteDatabase
        QuoteDatabase(DB_CONFIG)

        mock_psycopg2.connect.assert_called_once_with(
            host="localhost",
            port=5434,
            user="scott",
            password="secret",
            dbname="stock_quotes",
        )

    @patch("alphavantage.db_utils.psycopg2")
    def test_connect_sets_autocommit_false(self, mock_psycopg2):
        mock_conn = MagicMock()
        mock_conn.closed = 0
        mock_psycopg2.connect.return_value = mock_conn

        from alphavantage.db_utils import QuoteDatabase
        QuoteDatabase(DB_CONFIG)

        assert mock_conn.autocommit is False

    @patch("alphavantage.db_utils.psycopg2")
    def test_connect_raises_on_error(self, mock_psycopg2):
        mock_psycopg2.connect.side_effect = Exception("connection refused")
        mock_psycopg2.Error = Exception

        from alphavantage.db_utils import QuoteDatabase
        with pytest.raises(Exception, match="connection refused"):
            QuoteDatabase(DB_CONFIG)


# ---------------------------------------------------------------------------
# create_tables()
# ---------------------------------------------------------------------------

class TestCreateTables:
    @patch("alphavantage.db_utils.psycopg2")
    def test_create_tables_commits(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        db.create_tables()

        mock_conn.commit.assert_called_once()

    @patch("alphavantage.db_utils.psycopg2")
    def test_create_tables_closes_cursor(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        db.create_tables()

        mock_cursor.close.assert_called_once()

    @patch("alphavantage.db_utils.psycopg2")
    def test_create_tables_rolls_back_on_error(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        # Must raise the real psycopg2.Error so the except clause in db_utils catches it
        mock_cursor.execute.side_effect = _psycopg2.Error("syntax error")
        mock_conn.cursor.return_value = mock_cursor

        with pytest.raises(_psycopg2.Error):
            db.create_tables()

        mock_conn.rollback.assert_called_once()

    @patch("alphavantage.db_utils.psycopg2")
    def test_create_tables_creates_quotes_and_index_tables(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        db.create_tables()

        all_sql = " ".join(str(c.args[0]).lower() for c in mock_cursor.execute.call_args_list)
        assert "quotes" in all_sql
        assert "asset_indexes" in all_sql
        assert "index_members" in all_sql
        assert "index_weights" in all_sql
        assert "index_history" in all_sql


# ---------------------------------------------------------------------------
# save_quotes()
# ---------------------------------------------------------------------------

def _make_quotes_df():
    """Build a minimal quotes DataFrame matching what make_dataframes_list produces.

    The real DataFrames from make_dataframes_list have an *unnamed* string index
    (the date keys from the API JSON), so to_records(index=True) creates a field
    named 'index' rather than 'date'.  Use an unnamed index here to match that.
    """
    dates = ["2025-01-22", "2025-01-23"]
    df = pd.DataFrame({
        "namespace": ["NASDAQ", "NASDAQ"],
        "symbol": ["AAPL", "AAPL"],
        "close": [150.0, 152.0],
        "currency": ["USD", "USD"],
    }, index=pd.Index(dates))
    return df


def _make_quotes_df_numpy():
    """DataFrame with np.float64 close values — mirrors what _process_record produces."""
    import numpy as np
    dates = ["2025-01-22", "2025-01-23"]
    df = pd.DataFrame({
        "namespace": ["NASDAQ", "NASDAQ"],
        "symbol": ["GTC", "GTC"],
        "close": np.array([150.0, 152.0], dtype=np.float64),
        "currency": ["USD", "USD"],
    }, index=pd.Index(dates))
    return df


class TestSaveQuotes:
    @patch("alphavantage.db_utils.psycopg2")
    def test_save_quotes_calls_execute_values(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        db.save_quotes(_make_quotes_df())

        mock_psycopg2.extras.execute_values.assert_called_once()

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_quotes_passes_correct_row_count(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        df = _make_quotes_df()
        db.save_quotes(df)

        _, call_args, _ = mock_psycopg2.extras.execute_values.mock_calls[0]
        data = call_args[2]
        assert len(data) == len(df)

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_quotes_commits(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        db.save_quotes(_make_quotes_df())

        mock_conn.commit.assert_called_once()

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_quotes_rolls_back_on_error(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.extras.execute_values.side_effect = _psycopg2.Error("insert failed")

        with pytest.raises(_psycopg2.Error):
            db.save_quotes(_make_quotes_df())

        mock_conn.rollback.assert_called_once()

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_quotes_close_values_are_plain_float(self, mock_psycopg2):
        """np.float64 must be cast to plain float before passing to psycopg2."""
        import numpy as np
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        db.save_quotes(_make_quotes_df_numpy())

        _, call_args, _ = mock_psycopg2.extras.execute_values.mock_calls[0]
        data = call_args[2]
        for row in data:
            assert type(row[3]) is float, f"expected float, got {type(row[3])}"

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_quotes_upsert_sql_contains_on_conflict(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        db.save_quotes(_make_quotes_df())

        _, call_args, _ = mock_psycopg2.extras.execute_values.mock_calls[0]
        sql = call_args[1].lower()
        assert "on conflict" in sql
        assert "do update" in sql


# ---------------------------------------------------------------------------
# read_quotes()
# ---------------------------------------------------------------------------

class TestReadQuotes:
    def _rows(self):
        return [
            (date(2025, 1, 22), "AAPL", "NASDAQ", 150.0, "USD"),
            (date(2025, 1, 23), "AAPL", "NASDAQ", 152.0, "USD"),
        ]

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_quotes_no_filters(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = self._rows()
        mock_conn.cursor.return_value = mock_cursor

        result = db.read_quotes()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["date", "symbol", "namespace", "close", "currency"]

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_quotes_with_start_date(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = self._rows()
        mock_conn.cursor.return_value = mock_cursor

        db.read_quotes(start_date="2025-01-22")

        sql = mock_cursor.execute.call_args[0][0].lower()
        assert "date >= %s" in sql

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_quotes_with_end_date(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = self._rows()
        mock_conn.cursor.return_value = mock_cursor

        db.read_quotes(end_date="2025-01-23")

        sql = mock_cursor.execute.call_args[0][0].lower()
        assert "date <= %s" in sql

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_quotes_with_symbols(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = self._rows()
        mock_conn.cursor.return_value = mock_cursor

        db.read_quotes(symbols=["AAPL", "MSFT"])

        sql = mock_cursor.execute.call_args[0][0].lower()
        assert "symbol in" in sql

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_quotes_date_column_is_datetime(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = self._rows()
        mock_conn.cursor.return_value = mock_cursor

        result = db.read_quotes()

        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_quotes_empty_result(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        result = db.read_quotes()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# save_index_definition() / read_index_definitions()
# ---------------------------------------------------------------------------

class TestIndexDefinitions:
    def _index_cfg(self, itype="EQUAL_WEIGHT", with_mcap=False):
        cfg = {
            "NAME": "test_index",
            "TYPE": itype,
            "CREATED_DATE": "2025-01-22",
            "MEMBERS": ["AAPL", "MSFT"],
        }
        if with_mcap:
            cfg["MARKET_CAP"] = [2000.0, 3000.0]
        return cfg

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_definition_commits(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor

        db.save_index_definition(self._index_cfg())

        mock_conn.commit.assert_called_once()

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_definition_inserts_members(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor

        db.save_index_definition(self._index_cfg(with_mcap=True))

        _, call_args, _ = mock_psycopg2.extras.execute_values.mock_calls[0]
        rows = call_args[2]
        assert len(rows) == 2
        assert rows[0][1] == "AAPL"
        assert rows[0][2] == 2000.0
        assert rows[1][1] == "MSFT"

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_definition_null_market_cap_for_equal_weight(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor

        db.save_index_definition(self._index_cfg(itype="EQUAL_WEIGHT"))

        _, call_args, _ = mock_psycopg2.extras.execute_values.mock_calls[0]
        rows = call_args[2]
        assert all(r[2] is None for r in rows)

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_definitions_returns_asset_indexes_key(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [(1, "test_equal", "EQUAL_WEIGHT", date(2025, 1, 22), 10000.0)],
            [("AAPL", None), ("MSFT", None)],
        ]
        mock_conn.cursor.return_value = mock_cursor

        result = db.read_index_definitions()

        assert "asset_indexes" in result
        assert len(result["asset_indexes"]) == 1
        entry = result["asset_indexes"][0]
        assert entry["NAME"] == "test_equal"
        assert entry["TYPE"] == "EQUAL_WEIGHT"
        assert entry["MEMBERS"] == ["AAPL", "MSFT"]
        assert "MARKET_CAP" not in entry

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_definitions_includes_market_cap_when_present(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [(1, "test_mcap", "MARKET_CAP", date(2025, 1, 22), 10000.0)],
            [("AAPL", 2000.0), ("MSFT", 3000.0)],
        ]
        mock_conn.cursor.return_value = mock_cursor

        result = db.read_index_definitions()

        entry = result["asset_indexes"][0]
        assert entry["MARKET_CAP"] == [2000.0, 3000.0]

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_definitions_empty_db(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        result = db.read_index_definitions()

        assert result == {"asset_indexes": []}


# ---------------------------------------------------------------------------
# save_index_weights() / read_index_weights()
# ---------------------------------------------------------------------------

class TestIndexWeights:
    @patch("alphavantage.db_utils.psycopg2")
    def test_save_weights_commits(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor

        db.save_index_weights("test_index", {"AAPL": 50.0, "MSFT": 25.0})

        mock_conn.commit.assert_called_once()

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_weights_skips_when_index_not_found(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor

        db.save_index_weights("nonexistent", {"AAPL": 50.0})

        mock_conn.commit.assert_not_called()

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_weights_returns_dict(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("AAPL", 50.0), ("MSFT", 25.0)]
        mock_conn.cursor.return_value = mock_cursor

        result = db.read_index_weights("test_index")

        assert result == {"AAPL": 50.0, "MSFT": 25.0}

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_weights_empty_returns_empty_dict(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        result = db.read_index_weights("nonexistent")

        assert result == {}


# ---------------------------------------------------------------------------
# save_index_history() / read_index_history()
# ---------------------------------------------------------------------------

class TestIndexHistory:
    def _series(self):
        dates = pd.date_range("2025-01-22", periods=3, freq="B")
        return pd.Series([10000.0, 10100.0, 9950.0], index=dates, name="test_index")

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_history_commits(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor

        db.save_index_history("test_index", self._series())

        mock_conn.commit.assert_called_once()

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_history_skips_when_index_not_found(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor

        db.save_index_history("nonexistent", self._series())

        mock_conn.commit.assert_not_called()

    @patch("alphavantage.db_utils.psycopg2")
    def test_save_history_drops_nan_values(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor

        s = self._series().copy()
        s.iloc[1] = float("nan")
        db.save_index_history("test_index", s)

        _, call_args, _ = mock_psycopg2.extras.execute_values.mock_calls[0]
        rows = call_args[2]
        assert len(rows) == 2

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_history_returns_series(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (date(2025, 1, 22), 10000.0),
            (date(2025, 1, 23), 10100.0),
        ]
        mock_conn.cursor.return_value = mock_cursor

        result = db.read_index_history("test_index")

        assert isinstance(result, pd.Series)
        assert len(result) == 2
        assert result.name == "test_index"

    @patch("alphavantage.db_utils.psycopg2")
    def test_read_history_empty_returns_empty_series(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        result = db.read_index_history("nonexistent")

        assert isinstance(result, pd.Series)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

class TestClose:
    @patch("alphavantage.db_utils.psycopg2")
    def test_close_when_connected(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_conn.closed = 0

        db.close()

        mock_conn.close.assert_called_once()

    @patch("alphavantage.db_utils.psycopg2")
    def test_close_when_already_closed(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        mock_conn.closed = 1

        db.close()

        mock_conn.close.assert_not_called()

    @patch("alphavantage.db_utils.psycopg2")
    def test_close_when_connection_is_none(self, mock_psycopg2):
        db, mock_conn = make_db(mock_psycopg2)
        db.connection = None

        db.close()  # should not raise
