import json
import logging

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pandas.tseries.offsets import *


class AssetIndex():
    INDEX_FILE = "./indexes.json"
    COMPARE_INDEX_FILE = "./data/compare_index.pdf"

    def __init__(self, dfs, portfolio_value=10000, filename=INDEX_FILE):
        with open(filename, "r") as fin:
            config = json.load(fin)
            logging.info(f"read from {filename}: {len(config)} records")
        self.indexes_list = config["asset_indexes"]
        self.symbols_list = self._get_index_symbols()
        logging.info(f"loaded {len(self.symbols_list)} symbols")

        # Reindex data frame making each ticker with prices for each date
        self.dfs = dfs[["date", "symbol", "close"]].pivot_table("close", index="date", columns="symbol")
        # self.dfs.reset_index(drop=False, inplace=True)
        self.dfs = self.dfs[self.symbols_list]
        self.dfs.dropna(axis=1, how="all", inplace=True)
        logging.info(f"dataframe stats {self.dfs.describe()}")
        logging.info(f"dataframe info {self.dfs.info()}")

        logging.info(f"prices for all symbols: {self._verify_symbols()}")
        self.portfolio_value = portfolio_value
        self.portfolios = {}
        self._setup_portfolios()

        self._calculate_indexes()

    def _get_index_symbols(self):
        symbols_in_indexes = set()
        for indexes in self.indexes_list:
            symbols_in_indexes.update(indexes["MEMBERS"])
        return list(symbols_in_indexes)

    def _verify_symbols(self):
        present = []
        for x in self.symbols_list:
            present.append(x in self.dfs.columns)
        return np.array(present).all()

    def _setup_portfolios(self):
        """Set up portfolios for each index based on the start date."""
        for idx in self.indexes_list:
            index_name = idx["NAME"]
            index_members = idx["MEMBERS"]
            index_size = len(index_members)
            portfolio_start_date = idx.get("CREATED_DATE", self.dfs.index.min())
            logging.info(f"processing {index_name} with members {index_members} and start date {portfolio_start_date}")

            # Verify that is a complete set of prices for the index at the start date
            if not all(self.dfs[self.dfs.index == portfolio_start_date]) is True:
                logging.error(
                    f"Error: not all symbols have prices for {portfolio_start_date}. Portfolio will be incomplete!")

            # Set up portfolio based on the index type
            if index_name == "equal_weight_price_index":
                portfolio = {i: self.portfolio_value /
                                (index_size * self.dfs[self.dfs.index == portfolio_start_date][i].values[0]) for i in
                             index_members}
                logging.info(f"portfolio = {portfolio}")
                self.portfolios[index_name] = portfolio
            elif index_name == "constant_index":
                sum_of_prices = sum(
                    [self.dfs[self.dfs.index == portfolio_start_date][i].values[0] for i in index_members])
                portfolio = {i: self.portfolio_value /
                                sum_of_prices for i in index_members}
                logging.info(f"portfolio = {portfolio}")
                self.portfolios[index_name] = portfolio
            elif index_name == "market_cap_index":
                market_caps = dict(zip(idx["MEMBERS"], idx["MARKET_CAP"]))
                sum_market_caps = sum(idx["MARKET_CAP"])
                portfolio = {i: self.portfolio_value * market_caps[i] / (
                        self.dfs[self.dfs.index == portfolio_start_date][i].values[0] * sum_market_caps)
                             for i in index_members}
                logging.info(f"portfolio = {portfolio}")
                self.portfolios[index_name] = portfolio

    def get_portfolio(self, index_name):
        return self.portfolios[index_name]

    def _calculate_indexes(self):

        """Calculate the indexes based on the portfolios."""
        for index_name, portfolio in self.portfolios.items():
            logging.info(f"Calculating index {index_name} with portfolio {portfolio}")
            # Calculate the index value for each date
            self.dfs[index_name] = 0.0
            for member_symbol, shares in portfolio.items():
                self.dfs[index_name] += self.dfs[member_symbol] * shares
            logging.info(f"Index {index_name} calculated successfully.")

    def get_comparison_dataframe(self, index_name, comparison_portfolio):
        logging.info(f"index_name = {index_name}, comparison = {comparison_portfolio}")
        portfolio = self.portfolios[index_name]
        logging.info(f"index portfolio = {portfolio}")

        # Comparison is {symbol: shares} for comparison folder
        comparison_symbol = list(comparison_portfolio.keys())[0]
        comparison_index_name = f"{comparison_symbol}_comparison"
        comparison_shares = list(comparison_portfolio.values())[0]
        if comparison_shares == 0:
            # Calculate from portfolio value on portfolio start date
            for idx in self.indexes_list:
                if idx["NAME"] == index_name:
                    portfolio_start_date = idx.get("CREATED_DATE", self.dfs.index.min())
                    logging.info(f"portfolio start date = {portfolio_start_date}")
                    break
            comparison_shares = self.portfolio_value / \
                                self.dfs[self.dfs.index == portfolio_start_date][comparison_symbol].values[0]
        logging.info(f"comparison ticker = {comparison_symbol}, comparison shares = {comparison_shares}")

        # addd value for comparison portfolio
        self.dfs[comparison_index_name] = self.dfs[comparison_symbol] * comparison_shares
        logging.info(f"Index {index_name} calculated successfully.")
        df = self.dfs[[index_name, comparison_index_name]].copy()
        return df.dropna(axis=0, how="all").dropna(axis=1, how="all").sort_index(ascending=True)

    def plot_quotes(self, df, filename=COMPARE_INDEX_FILE):
        with PdfPages(filename) as pdf:
            logging.info("plotting {} dataframes".format(len(df)))
            fig = df.plot(figsize=[10, 5]).get_figure()
            pdf.savefig(fig)
            plt.close()
