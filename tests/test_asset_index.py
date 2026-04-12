"""
Unit tests for market_indexes/asset_index.py.

Portfolio weight calculations use real DataFrames with known values so the
math can be verified. DB integration points are tested with a mock db.
"""

import pytest
import json
from unittest.mock import MagicMock, patch, mock_open
import pandas as pd
import numpy as np

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CREATED_DATE = "2025-01-22"

# Prices on the created date: AAPL=100, MSFT=200, GOOG=150
PRICES = {
    "AAPL": [100.0, 102.0, 101.0, 103.0, 105.0],
    "MSFT": [200.0, 198.0, 202.0, 200.0, 204.0],
    "GOOG": [150.0, 152.0, 149.0, 151.0, 153.0],
}


@pytest.fixture
def sample_dfs():
    """Wide-format DataFrame with 5 business days starting on CREATED_DATE."""
    dates = pd.date_range(CREATED_DATE, periods=5, freq="B")
    return pd.DataFrame(PRICES, index=dates)


@pytest.fixture
def equal_weight_config():
    return {
        "asset_indexes": [{
            "NAME": "test_equal",
            "TYPE": "EQUAL_WEIGHT",
            "CREATED_DATE": CREATED_DATE,
            "MEMBERS": ["AAPL", "MSFT"],
        }]
    }


@pytest.fixture
def constant_config():
    return {
        "asset_indexes": [{
            "NAME": "test_constant",
            "TYPE": "CONSTANT",
            "CREATED_DATE": CREATED_DATE,
            "MEMBERS": ["AAPL", "MSFT"],
        }]
    }


@pytest.fixture
def market_cap_config():
    return {
        "asset_indexes": [{
            "NAME": "test_mcap",
            "TYPE": "MARKET_CAP",
            "CREATED_DATE": CREATED_DATE,
            "MEMBERS": ["AAPL", "MSFT"],
            "MARKET_CAP": [2000.0, 3000.0],
        }]
    }


@pytest.fixture
def multi_config():
    return {
        "asset_indexes": [
            {
                "NAME": "test_equal",
                "TYPE": "EQUAL_WEIGHT",
                "CREATED_DATE": CREATED_DATE,
                "MEMBERS": ["AAPL", "MSFT"],
            },
            {
                "NAME": "test_constant",
                "TYPE": "CONSTANT",
                "CREATED_DATE": CREATED_DATE,
                "MEMBERS": ["AAPL", "MSFT"],
            },
            {
                "NAME": "test_mcap",
                "TYPE": "MARKET_CAP",
                "CREATED_DATE": CREATED_DATE,
                "MEMBERS": ["AAPL", "MSFT"],
                "MARKET_CAP": [2000.0, 3000.0],
            },
        ]
    }


def make_asset_index(config, dfs, db=None):
    """Helper: create AssetIndex loading config from a mocked JSON file."""
    from market_indexes.asset_index import AssetIndex
    with patch("builtins.open", mock_open(read_data=json.dumps(config))):
        return AssetIndex(dfs, portfolio_value=10000, db=db)


# ---------------------------------------------------------------------------
# Equal-weight portfolio
# ---------------------------------------------------------------------------

class TestEqualWeightPortfolio:
    """
    With portfolio_value=10000, AAPL=100, MSFT=200, 2 members:
      AAPL shares = 10000 / (2 * 100) = 50
      MSFT shares = 10000 / (2 * 200) = 25
    """

    def test_aapl_shares(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs)
        portfolio = ai.get_portfolio("test_equal")
        assert pytest.approx(portfolio["AAPL"], rel=1e-6) == 50.0

    def test_msft_shares(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs)
        portfolio = ai.get_portfolio("test_equal")
        assert pytest.approx(portfolio["MSFT"], rel=1e-6) == 25.0

    def test_initial_value_equals_portfolio_value(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs)
        portfolio = ai.get_portfolio("test_equal")
        start = pd.Timestamp(CREATED_DATE)
        initial_value = sum(
            shares * sample_dfs.loc[start, sym]
            for sym, shares in portfolio.items()
        )
        assert pytest.approx(initial_value, rel=1e-6) == 10000.0


# ---------------------------------------------------------------------------
# Constant portfolio
# ---------------------------------------------------------------------------

class TestConstantPortfolio:
    """
    With portfolio_value=10000, AAPL=100, MSFT=200:
      total_price = 300
      shares per symbol = 10000 / 300 ≈ 33.333...
    """

    def test_both_symbols_have_equal_shares(self, sample_dfs, constant_config):
        ai = make_asset_index(constant_config, sample_dfs)
        portfolio = ai.get_portfolio("test_constant")
        assert pytest.approx(portfolio["AAPL"], rel=1e-6) == portfolio["MSFT"]

    def test_shares_value(self, sample_dfs, constant_config):
        ai = make_asset_index(constant_config, sample_dfs)
        portfolio = ai.get_portfolio("test_constant")
        expected = 10000.0 / (100.0 + 200.0)
        assert pytest.approx(portfolio["AAPL"], rel=1e-6) == expected

    def test_initial_value_equals_portfolio_value(self, sample_dfs, constant_config):
        ai = make_asset_index(constant_config, sample_dfs)
        portfolio = ai.get_portfolio("test_constant")
        start = pd.Timestamp(CREATED_DATE)
        initial_value = sum(
            shares * sample_dfs.loc[start, sym]
            for sym, shares in portfolio.items()
        )
        assert pytest.approx(initial_value, rel=1e-6) == 10000.0


# ---------------------------------------------------------------------------
# Market-cap portfolio
# ---------------------------------------------------------------------------

class TestMarketCapPortfolio:
    """
    AAPL mcap=2000, MSFT mcap=3000, total=5000
    AAPL weight=0.4, MSFT weight=0.6
    AAPL shares = 10000 * 0.4 / 100 = 40
    MSFT shares = 10000 * 0.6 / 200 = 30
    """

    def test_aapl_shares(self, sample_dfs, market_cap_config):
        ai = make_asset_index(market_cap_config, sample_dfs)
        portfolio = ai.get_portfolio("test_mcap")
        assert pytest.approx(portfolio["AAPL"], rel=1e-6) == 40.0

    def test_msft_shares(self, sample_dfs, market_cap_config):
        ai = make_asset_index(market_cap_config, sample_dfs)
        portfolio = ai.get_portfolio("test_mcap")
        assert pytest.approx(portfolio["MSFT"], rel=1e-6) == 30.0

    def test_initial_value_equals_portfolio_value(self, sample_dfs, market_cap_config):
        ai = make_asset_index(market_cap_config, sample_dfs)
        portfolio = ai.get_portfolio("test_mcap")
        start = pd.Timestamp(CREATED_DATE)
        initial_value = sum(
            shares * sample_dfs.loc[start, sym]
            for sym, shares in portfolio.items()
        )
        assert pytest.approx(initial_value, rel=1e-6) == 10000.0


# ---------------------------------------------------------------------------
# _calculate_indexes() — output columns
# ---------------------------------------------------------------------------

class TestCalculateIndexes:
    def test_index_column_added_to_dfs(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs)
        assert "test_equal" in ai.dfs.columns

    def test_all_index_columns_present(self, sample_dfs, multi_config):
        ai = make_asset_index(multi_config, sample_dfs)
        for idx in multi_config["asset_indexes"]:
            assert idx["NAME"] in ai.dfs.columns

    def test_index_values_start_at_portfolio_value(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs)
        start = pd.Timestamp(CREATED_DATE)
        assert pytest.approx(ai.dfs.loc[start, "test_equal"], rel=1e-6) == 10000.0

    def test_index_series_length_matches_input(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs)
        assert len(ai.dfs["test_equal"]) == len(sample_dfs)

    def test_index_values_are_numeric(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs)
        assert pd.api.types.is_float_dtype(ai.dfs["test_equal"])


# ---------------------------------------------------------------------------
# _load_config() — DB vs JSON fallback
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_loads_from_json_when_no_db(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs, db=None)
        assert len(ai.indexes_list) == 1
        assert ai.indexes_list[0]["NAME"] == "test_equal"

    def test_loads_from_db_when_db_has_definitions(self, sample_dfs, equal_weight_config, multi_config):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = multi_config

        ai = make_asset_index(equal_weight_config, sample_dfs, db=mock_db)

        mock_db.read_index_definitions.assert_called_once()
        assert len(ai.indexes_list) == 3

    def test_falls_back_to_json_when_db_returns_empty(self, sample_dfs, equal_weight_config):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = {"asset_indexes": []}

        ai = make_asset_index(equal_weight_config, sample_dfs, db=mock_db)

        assert len(ai.indexes_list) == 1
        assert ai.indexes_list[0]["NAME"] == "test_equal"

    def test_falls_back_to_json_when_db_raises(self, sample_dfs, equal_weight_config):
        mock_db = MagicMock()
        mock_db.read_index_definitions.side_effect = Exception("db down")

        ai = make_asset_index(equal_weight_config, sample_dfs, db=mock_db)

        assert len(ai.indexes_list) == 1


# ---------------------------------------------------------------------------
# DB persistence hooks in _initialize_portfolios() and _calculate_indexes()
# ---------------------------------------------------------------------------

class TestDatabasePersistence:
    def test_save_index_weights_called_per_index(self, sample_dfs, multi_config):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = multi_config

        make_asset_index(multi_config, sample_dfs, db=mock_db)

        assert mock_db.save_index_weights.call_count == 3

    def test_save_index_history_called_per_index(self, sample_dfs, multi_config):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = multi_config

        make_asset_index(multi_config, sample_dfs, db=mock_db)

        assert mock_db.save_index_history.call_count == 3

    def test_save_index_weights_called_with_correct_name(self, sample_dfs, equal_weight_config):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = equal_weight_config

        make_asset_index(equal_weight_config, sample_dfs, db=mock_db)

        call_name = mock_db.save_index_weights.call_args[0][0]
        assert call_name == "test_equal"

    def test_save_index_history_called_with_series(self, sample_dfs, equal_weight_config):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = equal_weight_config

        make_asset_index(equal_weight_config, sample_dfs, db=mock_db)

        _, call_args, _ = mock_db.save_index_history.mock_calls[0]
        series = call_args[1]
        assert isinstance(series, pd.Series)
        assert len(series) == len(sample_dfs)

    def test_db_weight_error_does_not_abort_calculation(self, sample_dfs, equal_weight_config):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = equal_weight_config
        mock_db.save_index_weights.side_effect = Exception("db write failed")

        # Should not raise — errors are caught and logged as warnings
        ai = make_asset_index(equal_weight_config, sample_dfs, db=mock_db)
        assert "test_equal" in ai.dfs.columns

    def test_db_history_error_does_not_abort_calculation(self, sample_dfs, equal_weight_config):
        mock_db = MagicMock()
        mock_db.read_index_definitions.return_value = equal_weight_config
        mock_db.save_index_history.side_effect = Exception("db write failed")

        ai = make_asset_index(equal_weight_config, sample_dfs, db=mock_db)
        assert "test_equal" in ai.dfs.columns

    def test_no_db_calls_when_db_is_none(self, sample_dfs, equal_weight_config):
        # With db=None nothing should blow up and no DB calls happen
        ai = make_asset_index(equal_weight_config, sample_dfs, db=None)
        assert "test_equal" in ai.dfs.columns


# ---------------------------------------------------------------------------
# get_portfolio()
# ---------------------------------------------------------------------------

class TestGetPortfolio:
    def test_returns_dict(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs)
        result = ai.get_portfolio("test_equal")
        assert isinstance(result, dict)

    def test_contains_expected_symbols(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs)
        result = ai.get_portfolio("test_equal")
        assert set(result.keys()) == {"AAPL", "MSFT"}

    def test_missing_index_raises(self, sample_dfs, equal_weight_config):
        ai = make_asset_index(equal_weight_config, sample_dfs)
        with pytest.raises(KeyError):
            ai.get_portfolio("nonexistent")
