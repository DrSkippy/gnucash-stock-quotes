"""
Unit tests for alphavantage/quotes.py.

QuoteDatabase and requests.get are mocked so no network or DB is needed.
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import json
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _stock_response(symbol="AAPL"):
    """Minimal Alpha Vantage TIME_SERIES_DAILY response."""
    return {
        "Meta Data": {
            "1. Information": "Daily Prices",
            "2. Symbol": symbol,
            "3. Last Refreshed": "2025-01-23",
        },
        "Time Series (Daily)": {
            "2025-01-23": {"1. open": "150", "2. high": "155", "3. low": "149", "4. close": "152", "5. volume": "1000000"},
            "2025-01-22": {"1. open": "148", "2. high": "151", "3. low": "147", "4. close": "150", "5. volume": "900000"},
            "2016-01-04": {"1. open": "100", "2. high": "102", "3. low": "99",  "4. close": "101", "5. volume": "500000"},
            "2015-12-31": {"1. open": "95",  "2. high": "97",  "3. low": "94",  "4. close": "96",  "5. volume": "400000"},
        },
    }


def _crypto_response(symbol="ETH"):
    """Minimal Alpha Vantage DIGITAL_CURRENCY_DAILY response."""
    return {
        "Meta Data": {
            "1. Information": "Digital Currency Daily",
            "2. Digital Currency Code": symbol,
        },
        "Time Series (Digital Currency Daily)": {
            "2025-01-23": {"1a. open (USD)": "3000", "2a. high (USD)": "3100", "3a. low (USD)": "2950", "4a. close (USD)": "3050", "5. volume": "5000"},
            "2025-01-22": {"1a. open (USD)": "2900", "2a. high (USD)": "3000", "3a. low (USD)": "2850", "4a. close (USD)": "2950", "5. volume": "4500"},
        },
    }


MINIMAL_CONFIG = {
    "configuration": {
        "key": "TESTKEY",
        "url_base": {
            "DIGITAL_CURRENCY_DAILY": "https://api.example.com/crypto?symbol={}&apikey={}",
            "TIME_SERIES_DAILY": "https://api.example.com/stocks?symbol={}&apikey={}",
        },
        "database": {
            "host": "localhost", "port": 5434,
            "user": "scott", "password": "secret", "database": "stock_quotes",
        },
    },
    "tickers": {
        "DIGITAL_CURRENCY_DAILY": ["ETH"],
        "TIME_SERIES_DAILY": ["AAPL"],
    },
}


def make_ticker_quotes(mock_db_cls):
    """Instantiate TickerQuotes with a mocked DB and config file."""
    mock_db = MagicMock()
    mock_db_cls.return_value = mock_db
    from alphavantage.quotes import TickerQuotes
    with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
        tq = TickerQuotes()
    return tq, mock_db


# ---------------------------------------------------------------------------
# _process_record()
# ---------------------------------------------------------------------------

class TestProcessRecord:
    def setup_method(self):
        with patch("alphavantage.db_utils.psycopg2"):
            with patch("alphavantage.quotes.QuoteDatabase"):
                with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
                    from alphavantage.quotes import TickerQuotes
                    self.tq = TickerQuotes()

    def test_stocks_returns_dataframe_and_symbol(self):
        df, symbol = self.tq._process_record(_stock_response("AAPL"))
        assert symbol == "AAPL"
        assert isinstance(df, pd.DataFrame)
        assert "close" in df.columns
        assert "symbol" in df.columns

    def test_stocks_close_is_float(self):
        df, _ = self.tq._process_record(_stock_response())
        assert df["close"].dtype == float

    def test_stocks_adds_currency_and_namespace(self):
        df, _ = self.tq._process_record(_stock_response())
        assert (df["currency"] == "USD").all()
        assert (df["namespace"] == "NASDAQ").all()

    def test_crypto_returns_dataframe_and_symbol(self):
        df, symbol = self.tq._process_record(_crypto_response("ETH"))
        assert symbol == "ETH"
        assert isinstance(df, pd.DataFrame)

    def test_missing_meta_data_returns_none(self):
        df, symbol = self.tq._process_record({"junk": "data"})
        assert df is None
        assert symbol is None

    def test_error_message_key_returns_none(self):
        response = _stock_response()
        response["Error Message"] = "Invalid API call"
        df, symbol = self.tq._process_record(response)
        assert df is None
        assert symbol is None

    def test_unknown_symbol_type_returns_none(self):
        response = {
            "Meta Data": {"1. Information": "something else"},
        }
        df, symbol = self.tq._process_record(response)
        assert df is None
        assert symbol is None


# ---------------------------------------------------------------------------
# make_dataframes_list()
# ---------------------------------------------------------------------------

class TestMakeDataframesList:
    def setup_method(self):
        with patch("alphavantage.db_utils.psycopg2"):
            with patch("alphavantage.quotes.QuoteDatabase"):
                with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
                    from alphavantage.quotes import TickerQuotes
                    self.tq = TickerQuotes()

    def test_returns_list_of_dataframes(self):
        results = [_stock_response("AAPL"), _stock_response("MSFT")]
        dfs = self.tq.make_dataframes_list(results)
        assert isinstance(dfs, list)
        assert all(isinstance(df, pd.DataFrame) for df in dfs)

    def test_filters_out_rows_before_2016(self):
        dfs = self.tq.make_dataframes_list([_stock_response()])
        df = dfs[0]
        assert (df.index > "2016-01-01").all()

    def test_columns_are_namespace_symbol_close_currency(self):
        dfs = self.tq.make_dataframes_list([_stock_response()])
        assert list(dfs[0].columns) == ["namespace", "symbol", "close", "currency"]

    def test_skips_error_records(self):
        results = [{"junk": "data"}, _stock_response("AAPL")]
        dfs = self.tq.make_dataframes_list(results)
        assert len(dfs) == 1

    def test_handles_all_error_records(self):
        dfs = self.tq.make_dataframes_list([{"junk": "data"}])
        assert dfs == []

    def test_multiple_tickers_returns_multiple_dfs(self):
        results = [_stock_response("AAPL"), _stock_response("MSFT")]
        dfs = self.tq.make_dataframes_list(results)
        assert len(dfs) == 2


# ---------------------------------------------------------------------------
# make_wide_dataframe()
# ---------------------------------------------------------------------------

class TestMakeWideDataframe:
    def setup_method(self):
        with patch("alphavantage.db_utils.psycopg2"):
            with patch("alphavantage.quotes.QuoteDatabase"):
                with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
                    from alphavantage.quotes import TickerQuotes
                    self.tq = TickerQuotes()

    def _long_df(self):
        return pd.DataFrame({
            "date": ["2025-01-22", "2025-01-22", "2025-01-23", "2025-01-23"],
            "symbol": ["AAPL", "MSFT", "AAPL", "MSFT"],
            "close": [150.0, 200.0, 152.0, 198.0],
        })

    def test_pivot_produces_symbol_columns(self):
        wide = self.tq.make_wide_dataframe(self._long_df())
        assert "AAPL" in wide.columns
        assert "MSFT" in wide.columns

    def test_pivot_indexed_by_date(self):
        wide = self.tq.make_wide_dataframe(self._long_df())
        assert wide.index.name == "date"

    def test_pivot_values_are_correct(self):
        wide = self.tq.make_wide_dataframe(self._long_df())
        assert wide.loc["2025-01-22", "AAPL"] == 150.0
        assert wide.loc["2025-01-23", "MSFT"] == 198.0


# ---------------------------------------------------------------------------
# concatenate_dataframes()
# ---------------------------------------------------------------------------

class TestConcatenateDataframes:
    def setup_method(self):
        with patch("alphavantage.db_utils.psycopg2"):
            with patch("alphavantage.quotes.QuoteDatabase"):
                with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
                    from alphavantage.quotes import TickerQuotes
                    self.tq = TickerQuotes()

    def test_list_of_dfs_concatenated(self):
        df1 = pd.DataFrame({"a": [1, 2]})
        df2 = pd.DataFrame({"a": [3, 4]})
        result = self.tq.concatenate_dataframes([df1, df2])
        assert len(result) == 4

    def test_single_df_returned_unchanged(self):
        df = pd.DataFrame({"a": [1, 2]})
        result = self.tq.concatenate_dataframes(df)
        assert result is df


# ---------------------------------------------------------------------------
# print_tickers()
# ---------------------------------------------------------------------------

class TestPrintTickers:
    def setup_method(self):
        with patch("alphavantage.db_utils.psycopg2"):
            with patch("alphavantage.quotes.QuoteDatabase"):
                with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
                    from alphavantage.quotes import TickerQuotes
                    self.tq = TickerQuotes()

    def test_prints_tickers_header(self, capsys):
        self.tq.print_tickers()
        out = capsys.readouterr().out
        assert "Tickers:" in out

    def test_prints_market_name(self, capsys):
        self.tq.print_tickers()
        out = capsys.readouterr().out
        assert "TIME_SERIES_DAILY" in out

    def test_prints_ticker_symbols(self, capsys):
        self.tq.print_tickers()
        out = capsys.readouterr().out
        assert "AAPL" in out


# ---------------------------------------------------------------------------
# fetch_quotes()
# ---------------------------------------------------------------------------

class TestFetchQuotes:
    def setup_method(self):
        with patch("alphavantage.db_utils.psycopg2"):
            with patch("alphavantage.quotes.QuoteDatabase"):
                with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
                    from alphavantage.quotes import TickerQuotes
                    self.tq = TickerQuotes()

    @patch("alphavantage.quotes.requests")
    def test_returns_list_of_responses(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"Meta Data": {}, "Time Series (Daily)": {}}
        mock_requests.get.return_value = mock_resp

        results = self.tq.fetch_quotes()

        assert isinstance(results, list)
        total_tickers = sum(len(v) for v in self.tq.tickers.values())
        assert len(results) == total_tickers

    @patch("alphavantage.quotes.requests")
    def test_calls_get_for_each_ticker(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_requests.get.return_value = mock_resp

        self.tq.fetch_quotes()

        n_tickers = sum(len(v) for v in self.tq.tickers.values())
        assert mock_requests.get.call_count == n_tickers


# ---------------------------------------------------------------------------
# save_quotes()
# ---------------------------------------------------------------------------

class TestSaveQuotes:
    def setup_method(self):
        with patch("alphavantage.db_utils.psycopg2"):
            with patch("alphavantage.quotes.QuoteDatabase"):
                with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
                    from alphavantage.quotes import TickerQuotes
                    self.tq = TickerQuotes()

    def test_writes_json_file(self, tmp_path):
        path = str(tmp_path / "quotes.json")
        self.tq.save_quotes([], filename=path)
        assert (tmp_path / "quotes.json").exists()

    def test_calls_db_save_for_each_df(self, tmp_path):
        path = str(tmp_path / "quotes.json")
        raw = [
            {
                "Meta Data": {
                    "2. Symbol": "AAPL",
                    "1. Information": "Daily",
                    "3. Last Refreshed": "2025-01-22",
                    "4. Output Size": "Compact",
                    "5. Time Zone": "US/Eastern",
                },
                "Time Series (Daily)": {
                    "2025-01-22": {
                        "1. open": "150", "2. high": "155",
                        "3. low": "148", "4. close": "152", "5. volume": "1000000",
                    }
                },
            }
        ]
        self.tq.save_quotes(raw, filename=path)
        self.tq.db.save_quotes.assert_called()


# ---------------------------------------------------------------------------
# read_quotes(filename=...)
# ---------------------------------------------------------------------------

class TestReadQuotesFromFile:
    def setup_method(self):
        with patch("alphavantage.db_utils.psycopg2"):
            with patch("alphavantage.quotes.QuoteDatabase"):
                with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
                    from alphavantage.quotes import TickerQuotes
                    self.tq = TickerQuotes()

    def test_reads_from_file_when_filename_given(self, tmp_path):
        import json as _json
        data_path = tmp_path / "quotes.json"
        data_path.write_text(_json.dumps([]))
        result = self.tq.read_quotes(filename=str(data_path))
        assert isinstance(result, list)

    def test_reads_from_db_when_no_filename(self):
        self.tq.db.read_quotes.return_value = MagicMock()
        self.tq.read_quotes()
        self.tq.db.read_quotes.assert_called_once()


# ---------------------------------------------------------------------------
# __del__()
# ---------------------------------------------------------------------------

class TestDel:
    def test_del_closes_db(self):
        with patch("alphavantage.db_utils.psycopg2"):
            with patch("alphavantage.quotes.QuoteDatabase") as mock_qdb_cls:
                with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
                    from alphavantage.quotes import TickerQuotes
                    tq = TickerQuotes()
                    mock_db = tq.db
                    tq.__del__()
                    mock_db.close.assert_called_once()

    def test_del_without_db_attribute(self):
        with patch("alphavantage.db_utils.psycopg2"):
            with patch("alphavantage.quotes.QuoteDatabase"):
                with patch("builtins.open", mock_open(read_data=json.dumps(MINIMAL_CONFIG))):
                    from alphavantage.quotes import TickerQuotes
                    tq = TickerQuotes()
                    del tq.db
                    tq.__del__()  # should not raise
