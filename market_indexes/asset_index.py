from typing import Dict, List, Set, Union
import json
import logging
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pandas.tseries.offsets import *


class AssetIndex:
    """Manages and calculates various types of asset indexes and portfolios."""

    # File paths
    INDEX_FILE = "./indexes.json"
    COMPARE_INDEX_FILE = "./data/compare_index.pdf"

    # Portfolio types
    EQUAL_WEIGHT = "equal_weight_price_index"
    CONSTANT_WEIGHT = "constant_index"
    MARKET_CAP_WEIGHT = "market_cap_index"

    def __init__(self, dfs: pd.DataFrame, portfolio_value: float = 10000, filename: str = INDEX_FILE):
        """
        Initialize AssetIndex with price data and configuration.
        
        Args:
            dfs: DataFrame containing price data
            portfolio_value: Initial portfolio value
            filename: Path to index configuration file
        """
        self.portfolio_value = portfolio_value
        self.portfolios: Dict[str, Dict[str, float]] = {}

        self.config = self._load_config(filename)
        self.indexes_list = self.config["asset_indexes"]
        self.symbols_list = self._get_unique_symbols()

        self.dfs = self._prepare_dataframe(dfs)
        self._verify_data_completeness()
        self._initialize_portfolios()
        self._calculate_indexes()

    def _load_config(self, filename: str) -> dict:
        """Load and validate index configuration."""
        with open(filename, "r") as fin:
            config = json.load(fin)
            logging.info(f"Read {len(config)} records from {filename}")
            return config

    def _get_unique_symbols(self) -> List[str]:
        """Extract unique symbols from all indexes."""
        symbols: Set[str] = set()
        for index in self.indexes_list:
            symbols.update(index["MEMBERS"])
        logging.info(f"Loaded {len(symbols)} unique symbols")
        return list(symbols)

    def _prepare_dataframe(self, dfs: pd.DataFrame) -> pd.DataFrame:
        """Prepare and clean the price data DataFrame."""
        df = dfs[["date", "symbol", "close"]].pivot_table(
            "close", index="date", columns="symbol"
        )
        df = df[self.symbols_list]
        df.dropna(axis=1, how="all", inplace=True)
        logging.info(f"DataFrame stats:\n{df.describe()}")
        return df

    def _verify_data_completeness(self) -> None:
        """Verify all required symbols have price data."""
        missing_symbols = [sym for sym in self.symbols_list if sym not in self.dfs.columns]
        if missing_symbols:
            logging.warning(f"Missing price data for symbols: {missing_symbols}")

    def _initialize_portfolios(self) -> None:
        """Initialize portfolios for all indexes."""
        portfolio_calculators = {
            self.EQUAL_WEIGHT: self._calculate_equal_weight_portfolio,
            self.CONSTANT_WEIGHT: self._calculate_constant_weight_portfolio,
            self.MARKET_CAP_WEIGHT: self._calculate_market_cap_portfolio
        }

        for idx in self.indexes_list:
            index_name = idx["NAME"]
            calculator = portfolio_calculators.get(index_name)
            if calculator:
                start_date = idx.get("CREATED_DATE", self.dfs.index.min())
                self.portfolios[index_name] = calculator(idx, start_date)
                logging.info(f"Initialized {index_name} portfolio")

    def _calculate_equal_weight_portfolio(self, index_config: dict, start_date: str) -> Dict[str, float]:
        """Calculate equal-weight portfolio allocations."""
        members = index_config["MEMBERS"]
        start_prices = self.dfs.loc[start_date, members]
        return {symbol: self.portfolio_value / (len(members) * price)
                for symbol, price in start_prices.items()}

    def _calculate_constant_weight_portfolio(self, index_config: dict, start_date: str) -> Dict[str, float]:
        """Calculate constant-weight portfolio allocations."""
        members = index_config["MEMBERS"]
        start_prices = self.dfs.loc[start_date, members]
        total_price = start_prices.sum()
        return {symbol: self.portfolio_value / total_price for symbol in members}

    def _calculate_market_cap_portfolio(self, index_config: dict, start_date: str) -> Dict[str, float]:
        """Calculate market-cap-weighted portfolio allocations."""
        members = index_config["MEMBERS"]
        market_caps = dict(zip(members, index_config["MARKET_CAP"]))
        start_prices = self.dfs.loc[start_date, members]
        total_mcap = sum(index_config["MARKET_CAP"])

        return {symbol: self.portfolio_value * market_caps[symbol] /
                        (price * total_mcap) for symbol, price in start_prices.items()}

    def get_portfolio(self, index_name: str) -> Dict[str, float]:
        """Get portfolio allocation for specified index."""
        return self.portfolios[index_name]

    def _calculate_indexes(self) -> None:
        """Calculate index values based on portfolio allocations."""
        for index_name, portfolio in self.portfolios.items():
            self.dfs[index_name] = sum(self.dfs[symbol] * shares
                                       for symbol, shares in portfolio.items())
            logging.info(f"Calculated {index_name} index values")

    def get_comparison_dataframe(self, index_name: str,
                                 comparison_portfolio: Dict[str, float]) -> pd.DataFrame:
        """Generate comparison DataFrame between index and reference portfolio."""
        symbol = next(iter(comparison_portfolio))
        shares = next(iter(comparison_portfolio.values()))

        if shares == 0:
            start_date = next(idx["CREATED_DATE"] for idx in self.indexes_list
                              if idx["NAME"] == index_name)
            shares = self.portfolio_value / self.dfs.loc[start_date, symbol]

        comparison_name = f"{symbol}_comparison"
        self.dfs[comparison_name] = self.dfs[symbol] * shares

        return self.dfs[[index_name, comparison_name]].dropna().sort_index()

    def plot_quotes(self, df: pd.DataFrame, filename: str = COMPARE_INDEX_FILE) -> None:
        """Plot and save comparison chart to PDF."""
        with PdfPages(filename) as pdf:
            fig = df.plot(figsize=[10, 5]).get_figure()
            pdf.savefig(fig)
            plt.close()
