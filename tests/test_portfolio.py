"""Unit tests for market_indexes/portfolio.py."""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch


def make_wide_df():
    dates = pd.date_range("2025-01-22", periods=10, freq="B")
    return pd.DataFrame({"AAPL": [150.0] * 10, "MSFT": [200.0] * 10}, index=dates)


def make_pa(mock_tq_cls, mock_ai_cls, tickers_file=None):
    """Helper: build a PortfolioAnalyzer with fully mocked dependencies."""
    mock_tq = MagicMock()
    mock_tq_cls.return_value = mock_tq
    mock_tq.read_quotes.return_value = pd.DataFrame()
    mock_tq.make_wide_dataframe.return_value = make_wide_df()
    mock_tq.db = MagicMock()

    mock_ai = MagicMock()
    mock_ai.dfs = make_wide_df()
    mock_ai_cls.return_value = mock_ai

    from market_indexes.portfolio import PortfolioAnalyzer
    if tickers_file:
        return PortfolioAnalyzer(tickers_file=tickers_file), mock_tq, mock_ai
    return PortfolioAnalyzer(), mock_tq, mock_ai


class TestPortfolioAnalyzerInit:
    @patch("market_indexes.portfolio.AssetIndex")
    @patch("market_indexes.portfolio.TickerQuotes")
    def test_default_init_uses_no_filename(self, mock_tq_cls, mock_ai_cls):
        pa, mock_tq, _ = make_pa(mock_tq_cls, mock_ai_cls)
        mock_tq_cls.assert_called_once_with()

    @patch("market_indexes.portfolio.AssetIndex")
    @patch("market_indexes.portfolio.TickerQuotes")
    def test_custom_file_passed_to_ticker_quotes(self, mock_tq_cls, mock_ai_cls):
        make_pa(mock_tq_cls, mock_ai_cls, tickers_file="/tmp/custom.json")
        mock_tq_cls.assert_called_once_with(filename="/tmp/custom.json")

    @patch("market_indexes.portfolio.AssetIndex")
    @patch("market_indexes.portfolio.TickerQuotes")
    def test_default_portfolio_value(self, mock_tq_cls, mock_ai_cls):
        pa, _, _ = make_pa(mock_tq_cls, mock_ai_cls)
        from market_indexes.portfolio import PortfolioAnalyzer
        assert pa.portfolio_value == PortfolioAnalyzer.DEFAULT_PORTFOLIO_VALUE

    @patch("market_indexes.portfolio.AssetIndex")
    @patch("market_indexes.portfolio.TickerQuotes")
    def test_asset_index_created_with_wide_df(self, mock_tq_cls, mock_ai_cls):
        make_pa(mock_tq_cls, mock_ai_cls)
        wide_df = mock_tq_cls.return_value.make_wide_dataframe.return_value
        mock_ai_cls.assert_called_once()
        call_args = mock_ai_cls.call_args
        pd.testing.assert_frame_equal(call_args[0][0], wide_df)


class TestLogPortfolioValue:
    @patch("market_indexes.portfolio.AssetIndex")
    @patch("market_indexes.portfolio.TickerQuotes")
    def test_returns_portfolio_dict(self, mock_tq_cls, mock_ai_cls):
        pa, _, mock_ai = make_pa(mock_tq_cls, mock_ai_cls)
        mock_ai.get_portfolio.return_value = {"AAPL": 10.5, "MSFT": 8.2}
        result = pa.log_portfolio_value("test_idx")
        assert result == {"AAPL": 10.5, "MSFT": 8.2}
        mock_ai.get_portfolio.assert_called_once_with("test_idx")


class TestAnalyzeAndPlot:
    @patch("market_indexes.portfolio.AssetIndex")
    @patch("market_indexes.portfolio.TickerQuotes")
    def test_calls_get_comparison_and_plot(self, mock_tq_cls, mock_ai_cls):
        pa, _, mock_ai = make_pa(mock_tq_cls, mock_ai_cls)
        cdf = pd.DataFrame({"a": [1], "b": [2]})
        mock_ai.get_comparison_dataframe.return_value = cdf

        pa.analyze_and_plot("test_idx", {"AAPL": 0}, "/tmp/out.pdf")

        mock_ai.get_comparison_dataframe.assert_called_once_with("test_idx", {"AAPL": 0})
        mock_ai.plot_quotes.assert_called_once_with(cdf, "/tmp/out.pdf")


class TestCorrelationsPlot:
    @patch("market_indexes.portfolio.CorrelationsPlotter")
    @patch("market_indexes.portfolio.AssetIndex")
    @patch("market_indexes.portfolio.TickerQuotes")
    def test_no_start_date_uses_full_df(self, mock_tq_cls, mock_ai_cls, mock_cp_cls):
        pa, _, mock_ai = make_pa(mock_tq_cls, mock_ai_cls)
        wide_df = make_wide_df()
        mock_ai.dfs = wide_df
        mock_cp = MagicMock()
        mock_cp_cls.return_value = mock_cp

        pa.correlations_plot(["AAPL", "MSFT"])

        mock_cp_cls.assert_called_once_with(wide_df)
        mock_cp.plot_correlation.assert_called_once_with("AAPL", "MSFT")

    @patch("market_indexes.portfolio.CorrelationsPlotter")
    @patch("market_indexes.portfolio.AssetIndex")
    @patch("market_indexes.portfolio.TickerQuotes")
    def test_start_date_filters_df(self, mock_tq_cls, mock_ai_cls, mock_cp_cls):
        pa, _, mock_ai = make_pa(mock_tq_cls, mock_ai_cls)
        wide_df = make_wide_df()  # 10 business days from 2025-01-22
        mock_ai.dfs = wide_df
        mock_cp = MagicMock()
        mock_cp_cls.return_value = mock_cp

        pa.correlations_plot(["AAPL", "MSFT"], start_date="2025-01-29")

        call_df = mock_cp_cls.call_args[0][0]
        assert len(call_df) < len(wide_df)
