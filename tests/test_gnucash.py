"""Unit tests for analyzer/gnucash.py."""

import pytest
import pandas as pd
from unittest.mock import patch


def make_df():
    return pd.DataFrame(
        {"close": [100.0, 200.0]},
        index=["2026-01-02", "2026-01-03"],
    )


class TestGnucash:
    def test_init_stores_path_and_dataframe(self, tmp_path):
        df = make_df()
        from analyzer.gnucash import Gnucash
        g = Gnucash(df, str(tmp_path / "prices.csv"))
        assert g.prices_file == str(tmp_path / "prices.csv")
        assert g.dataframe is df

    def test_save_gnucash_quotes_creates_file(self, tmp_path):
        path = str(tmp_path / "prices.csv")
        from analyzer.gnucash import Gnucash
        g = Gnucash(make_df(), path)
        g.save_gnucash_quotes()
        assert (tmp_path / "prices.csv").exists()

    def test_save_gnucash_quotes_no_header(self, tmp_path):
        path = str(tmp_path / "prices.csv")
        from analyzer.gnucash import Gnucash
        g = Gnucash(make_df(), path)
        g.save_gnucash_quotes()
        content = (tmp_path / "prices.csv").read_text()
        assert "close" not in content

    def test_save_gnucash_quotes_contains_values(self, tmp_path):
        path = str(tmp_path / "prices.csv")
        from analyzer.gnucash import Gnucash
        g = Gnucash(make_df(), path)
        g.save_gnucash_quotes()
        content = (tmp_path / "prices.csv").read_text()
        assert "100.0" in content
        assert "200.0" in content

    @patch("analyzer.gnucash.plot_stock_prices")
    def test_process_quotes_calls_plot(self, mock_plot, tmp_path):
        df = make_df()
        from analyzer.gnucash import Gnucash
        g = Gnucash(df, str(tmp_path / "prices.csv"))
        g.process_quotes()
        mock_plot.assert_called_once_with(df)

    @patch("analyzer.gnucash.plot_stock_prices")
    def test_process_quotes_writes_csv(self, mock_plot, tmp_path):
        path = str(tmp_path / "prices.csv")
        from analyzer.gnucash import Gnucash
        g = Gnucash(make_df(), path)
        g.process_quotes()
        assert (tmp_path / "prices.csv").exists()
