"""
Unit tests for analyzer/plots.py.

matplotlib and PdfPages are mocked so no files are written and no display
is needed.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import pandas as pd
import numpy as np
from datetime import date

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analyzer.plots import CorrelationsPlotter, plot_stock_prices, ANNOTATION_INTERVAL


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DATES = pd.date_range("2025-01-22", periods=14, freq="B")


@pytest.fixture
def wide_df():
    """Wide-format DataFrame: date index, one column per symbol."""
    return pd.DataFrame(
        {
            "AAPL": np.linspace(100.0, 114.0, 14),
            "MSFT": np.linspace(200.0, 227.0, 14),
        },
        index=DATES,
    )


@pytest.fixture
def deep_df():
    """Deep-format (long) DataFrame: symbol, date, close columns."""
    aapl = pd.DataFrame(
        {"symbol": "AAPL", "date": DATES, "close": np.linspace(100.0, 114.0, 14)}
    )
    msft = pd.DataFrame(
        {"symbol": "MSFT", "date": DATES, "close": np.linspace(200.0, 227.0, 14)}
    )
    return pd.concat([aapl, msft], ignore_index=True)


@pytest.fixture
def wide_plotter(wide_df):
    return CorrelationsPlotter(wide_df)


@pytest.fixture
def deep_plotter(deep_df):
    return CorrelationsPlotter(deep_df)


# ---------------------------------------------------------------------------
# CorrelationsPlotter.__init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_index_is_reset(self, wide_df):
        wide_df.index = range(10, 24)
        plotter = CorrelationsPlotter(wide_df)
        assert list(plotter.dataframes.index) == list(range(14))

    def test_dataframes_stored(self, wide_df):
        plotter = CorrelationsPlotter(wide_df)
        assert plotter.dataframes is not wide_df   # copy via reset_index
        assert "AAPL" in plotter.dataframes.columns


# ---------------------------------------------------------------------------
# _get_wide_ticker_data
# ---------------------------------------------------------------------------

class TestGetWideTicker:
    def test_returns_dataframe(self, wide_plotter):
        result = wide_plotter._get_wide_ticker_data("AAPL")
        assert isinstance(result, pd.DataFrame)

    def test_has_date_and_close_columns(self, wide_plotter):
        result = wide_plotter._get_wide_ticker_data("AAPL")
        assert "date" in result.columns
        assert "close" in result.columns

    def test_date_column_is_datetime(self, wide_plotter):
        result = wide_plotter._get_wide_ticker_data("AAPL")
        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    def test_symbol_column_added(self, wide_plotter):
        result = wide_plotter._get_wide_ticker_data("AAPL")
        assert "symbol" in result.columns
        assert (result["symbol"] == "AAPL").all()

    def test_close_values_correct(self, wide_plotter):
        result = wide_plotter._get_wide_ticker_data("AAPL")
        assert pytest.approx(result["close"].iloc[0], rel=1e-6) == 100.0

    def test_row_count_matches_input(self, wide_plotter):
        result = wide_plotter._get_wide_ticker_data("MSFT")
        assert len(result) == 14


# ---------------------------------------------------------------------------
# _get_deep_ticker_data
# ---------------------------------------------------------------------------

class TestGetDeepTicker:
    def test_returns_only_requested_symbol(self, deep_plotter):
        result = deep_plotter._get_deep_ticker_data("AAPL")
        assert (result["symbol"] == "AAPL").all()

    def test_excludes_other_symbols(self, deep_plotter):
        result = deep_plotter._get_deep_ticker_data("AAPL")
        assert "MSFT" not in result["symbol"].values

    def test_row_count_correct(self, deep_plotter):
        result = deep_plotter._get_deep_ticker_data("MSFT")
        assert len(result) == 14

    def test_returns_dataframe(self, deep_plotter):
        assert isinstance(deep_plotter._get_deep_ticker_data("AAPL"), pd.DataFrame)


# ---------------------------------------------------------------------------
# _prepare_correlation_data
# ---------------------------------------------------------------------------

class TestPrepareCorrelationData:
    def _make_dfs(self):
        df1 = pd.DataFrame({"date": DATES, "close": np.linspace(100.0, 114.0, 14),
                             "symbol": "AAPL"})
        df2 = pd.DataFrame({"date": DATES, "close": np.linspace(200.0, 227.0, 14),
                             "symbol": "MSFT"})
        return df1, df2

    def test_output_columns(self, wide_plotter):
        df1, df2 = self._make_dfs()
        result = wide_plotter._prepare_correlation_data(df1, df2, "AAPL", "MSFT")
        assert "close_AAPL" in result.columns
        assert "close_MSFT" in result.columns

    def test_index_is_date(self, wide_plotter):
        df1, df2 = self._make_dfs()
        result = wide_plotter._prepare_correlation_data(df1, df2, "AAPL", "MSFT")
        assert result.index.name == "date"

    def test_row_count(self, wide_plotter):
        df1, df2 = self._make_dfs()
        result = wide_plotter._prepare_correlation_data(df1, df2, "AAPL", "MSFT")
        assert len(result) == 14

    def test_values_aligned_correctly(self, wide_plotter):
        df1, df2 = self._make_dfs()
        result = wide_plotter._prepare_correlation_data(df1, df2, "AAPL", "MSFT")
        assert pytest.approx(result["close_AAPL"].iloc[0], rel=1e-6) == 100.0
        assert pytest.approx(result["close_MSFT"].iloc[0], rel=1e-6) == 200.0

    def test_asof_merge_handles_missing_dates(self, wide_plotter):
        """merge_asof fills forward when df2 is missing some dates."""
        df1 = pd.DataFrame({"date": DATES, "close": np.linspace(100.0, 114.0, 14),
                             "symbol": "AAPL"})
        # df2 has only every other date
        df2 = pd.DataFrame({"date": DATES[::2], "close": np.linspace(200.0, 226.0, 7),
                             "symbol": "MSFT"})
        result = wide_plotter._prepare_correlation_data(df1, df2, "AAPL", "MSFT")
        assert len(result) == 14
        assert result["close_MSFT"].notna().any()


# ---------------------------------------------------------------------------
# _plot_correlation_scatter
# ---------------------------------------------------------------------------

class TestPlotCorrelationScatter:
    def _make_merged_df(self):
        df = pd.DataFrame(
            {
                "close_AAPL": np.linspace(100.0, 114.0, 14),
                "close_MSFT": np.linspace(200.0, 227.0, 14),
            },
            index=DATES,
        )
        df.index.name = "date"
        return df

    @patch("analyzer.plots.plt")
    def test_axes_labels_set(self, mock_plt, wide_plotter):
        mock_pdf = MagicMock()
        mock_ax = MagicMock()
        mock_fig = MagicMock()
        mock_ax.get_figure.return_value = mock_fig

        with patch.object(self._make_merged_df().__class__, "plot", return_value=mock_ax):
            df = self._make_merged_df()
            with patch.object(df, "plot", return_value=mock_ax):
                wide_plotter._plot_correlation_scatter(df, "AAPL", "MSFT", mock_pdf)

        mock_plt.xlabel.assert_called_once_with("AAPL")
        mock_plt.ylabel.assert_called_once_with("MSFT")

    @patch("analyzer.plots.plt")
    def test_figure_saved_to_pdf(self, mock_plt, wide_plotter):
        mock_pdf = MagicMock()
        mock_ax = MagicMock()
        mock_fig = MagicMock()
        mock_ax.get_figure.return_value = mock_fig

        df = self._make_merged_df()
        with patch.object(df, "plot", return_value=mock_ax):
            wide_plotter._plot_correlation_scatter(df, "AAPL", "MSFT", mock_pdf)

        mock_pdf.savefig.assert_called_once_with(mock_fig)

    @patch("analyzer.plots.plt")
    def test_annotations_at_interval(self, mock_plt, wide_plotter):
        """annotate() should be called once per ANNOTATION_INTERVAL rows."""
        mock_pdf = MagicMock()
        mock_ax = MagicMock()
        mock_ax.get_figure.return_value = MagicMock()

        df = self._make_merged_df()
        with patch.object(df, "plot", return_value=mock_ax):
            wide_plotter._plot_correlation_scatter(df, "AAPL", "MSFT", mock_pdf)

        expected_annotations = len(df) // ANNOTATION_INTERVAL + (1 if len(df) % ANNOTATION_INTERVAL == 0 else 1)
        # rows 0, 7 → 2 annotations for 14 rows
        assert mock_ax.annotate.call_count == 2

    @patch("analyzer.plots.plt")
    def test_annotation_text_is_date_string(self, mock_plt, wide_plotter):
        mock_pdf = MagicMock()
        mock_ax = MagicMock()
        mock_ax.get_figure.return_value = MagicMock()

        df = self._make_merged_df()
        with patch.object(df, "plot", return_value=mock_ax):
            wide_plotter._plot_correlation_scatter(df, "AAPL", "MSFT", mock_pdf)

        first_annotation_text = mock_ax.annotate.call_args_list[0][0][0]
        # Should be a 10-char date string e.g. "2025-01-22"
        assert len(first_annotation_text) == 10
        assert first_annotation_text.startswith("2025-")


# ---------------------------------------------------------------------------
# plot_correlation() — dispatch and error handling
# ---------------------------------------------------------------------------

class TestPlotCorrelation:
    @patch("analyzer.plots.PdfPages")
    @patch("analyzer.plots.plt")
    def test_wide_format_dispatched(self, mock_plt, mock_pdf_cls, wide_plotter):
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(wide_plotter, "_get_wide_ticker_data",
                          wraps=wide_plotter._get_wide_ticker_data) as mock_wide, \
             patch.object(wide_plotter, "_get_deep_ticker_data") as mock_deep, \
             patch.object(wide_plotter, "_plot_single_ticker"), \
             patch.object(wide_plotter, "_prepare_correlation_data",
                          return_value=pd.DataFrame(
                              {"close_AAPL": [1.0], "close_MSFT": [2.0]},
                              index=pd.to_datetime(["2025-01-22"])
                          )) as mock_prep, \
             patch.object(wide_plotter, "_plot_correlation_scatter"):
            wide_plotter.plot_correlation("AAPL", "MSFT", filename="/tmp/test.pdf")

        mock_wide.assert_called()
        mock_deep.assert_not_called()

    @patch("analyzer.plots.PdfPages")
    @patch("analyzer.plots.plt")
    def test_deep_format_dispatched(self, mock_plt, mock_pdf_cls, deep_plotter):
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(deep_plotter, "_get_wide_ticker_data") as mock_wide, \
             patch.object(deep_plotter, "_get_deep_ticker_data",
                          wraps=deep_plotter._get_deep_ticker_data) as mock_deep, \
             patch.object(deep_plotter, "_plot_single_ticker"), \
             patch.object(deep_plotter, "_prepare_correlation_data",
                          return_value=pd.DataFrame(
                              {"close_AAPL": [1.0], "close_MSFT": [2.0]},
                              index=pd.to_datetime(["2025-01-22"])
                          )), \
             patch.object(deep_plotter, "_plot_correlation_scatter"):
            deep_plotter.plot_correlation("AAPL", "MSFT", filename="/tmp/test.pdf")

        mock_deep.assert_called()
        mock_wide.assert_not_called()

    def test_raises_when_ticker1_not_in_wide(self, wide_plotter):
        with pytest.raises(ValueError, match="NOPE"):
            wide_plotter.plot_correlation("NOPE", "MSFT")

    def test_raises_when_ticker2_not_in_wide(self, wide_plotter):
        with pytest.raises(ValueError, match="NOPE"):
            wide_plotter.plot_correlation("AAPL", "NOPE")

    def test_raises_when_ticker1_not_in_deep(self, deep_plotter):
        with pytest.raises(ValueError, match="NOPE"):
            deep_plotter.plot_correlation("NOPE", "MSFT")

    def test_raises_when_ticker2_not_in_deep(self, deep_plotter):
        with pytest.raises(ValueError, match="NOPE"):
            deep_plotter.plot_correlation("AAPL", "NOPE")

    @patch("analyzer.plots.PdfPages")
    @patch("analyzer.plots.plt")
    def test_single_ticker_plots_called_for_both(self, mock_plt, mock_pdf_cls, wide_plotter):
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(wide_plotter, "_plot_single_ticker") as mock_single, \
             patch.object(wide_plotter, "_prepare_correlation_data",
                          return_value=pd.DataFrame(
                              {"close_AAPL": [1.0], "close_MSFT": [2.0]},
                              index=pd.to_datetime(["2025-01-22"])
                          )), \
             patch.object(wide_plotter, "_plot_correlation_scatter"):
            wide_plotter.plot_correlation("AAPL", "MSFT", filename="/tmp/test.pdf")

        assert mock_single.call_count == 2
        called_tickers = {c[0][1] for c in mock_single.call_args_list}
        assert called_tickers == {"AAPL", "MSFT"}

    @patch("analyzer.plots.PdfPages")
    @patch("analyzer.plots.plt")
    def test_scatter_plot_called_once(self, mock_plt, mock_pdf_cls, wide_plotter):
        mock_pdf = MagicMock()
        mock_pdf_cls.return_value.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(wide_plotter, "_plot_single_ticker"), \
             patch.object(wide_plotter, "_prepare_correlation_data",
                          return_value=pd.DataFrame(
                              {"close_AAPL": [1.0], "close_MSFT": [2.0]},
                              index=pd.to_datetime(["2025-01-22"])
                          )), \
             patch.object(wide_plotter, "_plot_correlation_scatter") as mock_scatter:
            wide_plotter.plot_correlation("AAPL", "MSFT", filename="/tmp/test.pdf")

        mock_scatter.assert_called_once()


# ---------------------------------------------------------------------------
# plot_stock_prices()
# ---------------------------------------------------------------------------

class TestPlotStockPrices:
    @pytest.fixture
    def long_df(self):
        return pd.DataFrame({
            "symbol": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "date":   pd.to_datetime(["2025-01-22", "2025-01-23"] * 2),
            "close":  [100.0, 102.0, 200.0, 198.0],
        })

    @patch("analyzer.plots.PdfPages")
    @patch("analyzer.plots.plt")
    def test_plots_all_symbols_by_default(self, mock_plt, mock_pdf_cls, long_df):
        mock_pdf_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_pdf_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(CorrelationsPlotter, "_plot_single_ticker") as mock_plot:
            plot_stock_prices(long_df, filename="/tmp/test.pdf")

        called_tickers = [c[0][1] for c in mock_plot.call_args_list]
        assert set(called_tickers) == {"AAPL", "MSFT"}

    @patch("analyzer.plots.PdfPages")
    @patch("analyzer.plots.plt")
    def test_plots_only_requested_symbols(self, mock_plt, mock_pdf_cls, long_df):
        mock_pdf_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_pdf_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(CorrelationsPlotter, "_plot_single_ticker") as mock_plot:
            plot_stock_prices(long_df, filename="/tmp/test.pdf", symbols=["AAPL"])

        called_tickers = [c[0][1] for c in mock_plot.call_args_list]
        assert called_tickers == ["AAPL"]

    @patch("analyzer.plots.PdfPages")
    @patch("analyzer.plots.plt")
    def test_pdf_opened_at_given_path(self, mock_plt, mock_pdf_cls, long_df):
        mock_pdf_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_pdf_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(CorrelationsPlotter, "_plot_single_ticker"):
            plot_stock_prices(long_df, filename="/tmp/custom.pdf")

        mock_pdf_cls.assert_called_once_with("/tmp/custom.pdf")

    @patch("analyzer.plots.PdfPages")
    @patch("analyzer.plots.plt")
    def test_plt_close_called(self, mock_plt, mock_pdf_cls, long_df):
        mock_pdf_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_pdf_cls.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(CorrelationsPlotter, "_plot_single_ticker"):
            plot_stock_prices(long_df, filename="/tmp/test.pdf")

        mock_plt.close.assert_called_once()
