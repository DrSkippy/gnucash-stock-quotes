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
        self.symbols_list = self.get_index_symbols()
        logging.info(f"loaded {len(self.symbols_list)} symbols")
        self.dfs = dfs
        logging.info(f"prices for all symbols: {self.verify_symbols()}")
        self.portfolio_value = portfolio_value
        self.portfolios = {}
        self.index_start_prices = {}

    def get_index_symbols(self):
        symbols_in_indexes = set()
        for indexes in self.indexes_list:
            symbols_in_indexes.update(indexes["MEMBERS"])
        return list(symbols_in_indexes)

    def verify_symbols(self):
        present = []
        for x in self.symbols_list:
            present.append(x in self.dfs["symbol"].values)
        return np.array(present).all()

    def start_prices(self, start_date):
        for idx in self.indexes_list:
            index_prices = {}
            for member_symbol in idx["MEMBERS"]:
                df = self.dfs[(self.dfs.symbol == member_symbol) & (self.dfs.date == start_date)]
                if len(df) != 1:
                    logging.error(f"Error: no symbol, date match for ({member_symbol}, {start_date}). Start price will be incorrect!")
                index_prices[member_symbol] = df["close"].values[0]
            self.index_start_prices[idx["NAME"]] = index_prices
        return

    def set_up_indexes(self, start_date):
        # one comparison for each index defined
        for idx in self.indexes_list:
            index_name = idx["NAME"]
            index_members = idx["MEMBERS"]
            index_size = len(index_members)
            logging.info(f"processing {index_name} with members {index_members}")

            self.start_prices(start_date)
            logging.info(f"index_start_price = {self.index_start_prices[index_name]}")

            if index_name == "equal_weight_price_index":
                portfolio = {i: self.portfolio_value / (index_size * self.index_start_prices[index_name][i]) for i in index_members}
                logging.info(f"portfolio = {portfolio}")
                self.portfolios[index_name] = portfolio
            elif index_name == "constant_index":
                sum_of_prices = sum(self.index_start_prices[index_name].values())
                portfolio = {i: self.portfolio_value / sum_of_prices for i in index_members}
                logging.info(f"portfolio = {portfolio}")
                self.portfolios[index_name] = portfolio
            elif index_name == "market_cap_index":
                market_caps = dict(zip(idx["MEMBERS"], idx["MARKET_CAP"]))
                sum_market_caps = sum(idx["MARKET_CAP"])
                portfolio = {i: self.portfolio_value * market_caps[i] / (self.index_start_prices[index_name][i] * sum_market_caps)
                             for i in index_members}
                logging.info(f"portfolio = {portfolio}")
                self.portfolios[index_name] = portfolio

    def get_portfolio(self, index_name):
        return self.portfolios[index_name]

    def get_portfolio_value(self, index_name, value_date):
        portfolio = self.portfolios[index_name]
        value = 0
        for member_symbol in portfolio:
            df = self.dfs[(self.dfs.symbol == member_symbol) & (self.dfs.date == value_date)] # this is 1 row
            if len(df) != 1:
                logging.error(f"Error: no symbol, date match for ({member_symbol}, {value_date}). Portfolio value will be incorrect!")
            value += portfolio[member_symbol] * df["close"].values[0]
        logging.info(f"Index: {index_name} has value of Value = {value}")
        return value

    def get_comparison_dataframe(self, index_name, comparison_portfolio, start_date, end_date):
        logging.info(f"index_name = {index_name}, comparison = {comparison_portfolio}")
        logging.info(f"start_date = {start_date}, end_date = {end_date}")
        portfolio = self.portfolios[index_name]
        logging.info(f"portfolio = {portfolio}")
        # Test start and end dates match data
        if start_date not in self.dfs.date or end_data not in self.dfs.date:
            logging.error(f"start_date and end_data are not available for {start_date}, {end_date}, {index_name}")

        # Comparison is {symbol: shares} for comparison folder
        comp_key = list(comparison_portfolio.keys())[0]
        comp_value = list(comparison_portfolio.values())[0]
        logging.info(f"comp_key = {comp_key}, comp_value = {comp_value}")

        date_index = pd.date_range(start_date, end_date, freq=BDay())
        timeseries = {x.date().strftime("%Y-%m-%d"): [0.0, 0.0] for x in date_index}
        logging.info(f"length of timeseries = {len(timeseries)}")

        for member_symbol in portfolio:
            for i, value_date in enumerate(date_index):
                vd = value_date.date().strftime("%Y-%m-%d")
                try:
                    timeseries[vd][0] += self.dfs[(self.dfs.symbol == member_symbol) & (self.dfs.date == vd)]["close"].values[0] * \
                                         portfolio[member_symbol]
                except (IndexError, KeyError) as e:
                    logging.warning(f"key error for {member_symbol} at {vd} -- skipping")

        for i, value_date in enumerate(date_index):
            vd = value_date.date().strftime("%Y-%m-%d")
            try:
                timeseries[vd][1] = self.dfs[(self.dfs.symbol == comp_key) & (self.dfs.date == vd)]["close"].values[0] * comp_value
            except (IndexError, KeyError) as e:
                logging.warning(f"key error for {comp_key} at {vd} -- skipping")

        df = pd.DataFrame.from_dict(timeseries, orient="index", columns=[index_name, comp_key])
        return df.loc[(df != 0).any(axis=1)]  # Remove rows with all zeros
        #return df

    def plot_quotes(self, df, filename=COMPARE_INDEX_FILE):
        with PdfPages(filename) as pdf:
            logging.info("plotting {} dataframes".format(len(df)))
            fig = df.plot(figsize=[13, 8]).get_figure()
            pdf.savefig(fig)
            plt.close()
