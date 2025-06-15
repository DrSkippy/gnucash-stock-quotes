import json
import logging

import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pandas.tseries.offsets import *


class AssetIndex():

    INDEX_FILE = "./indexes.json"
    COMPARE_INDEX_FILE = "./data/compare_index.pdf"

    def __init__(self, filename=INDEX_FILE):
        with open(filename, "r") as fin:
            config = json.load(fin)
            logging.info(f"read from {filename}: {len(config)} records")
        self.indexes = config["asset_indexes"]
        self.portfolios = {}

    def set_up_indexes(self, dfs, start_date, investment=10000):
        # one comparison for each index defined
        for i in self.indexes:
            index_name = i["NAME"]
            index_members = i["MEMBERS"]
            index_size = len(index_members)
            logging.info(f"processing {index_name} with members {index_members}")
            index_start_prices = self.start_prices(dfs, index_members, start_date)
            logging.info(f"index_start_price = {index_start_prices}")
            if index_name == "equal_weight_price_index":
                portfolio = {i: investment / (index_size * index_start_prices[i]) for i in index_members}
                logging.debug(f"portfolio = {portfolio}")
                self.portfolios[index_name] = portfolio
            elif index_name == "constant_index":
                sum_of_prices = sum(index_start_prices.values())
                portfolio = {i: investment / sum_of_prices for i in index_members}
                logging.debug(f"portfolio = {portfolio}")
                self.portfolios[index_name] = portfolio
            elif index_name == "market_cap_index":
                market_caps = dict(zip(i["MEMBERS"], i["MARKET_CAP"]))
                sum_market_caps = sum(i["MARKET_CAP"])
                portfolio = {i: investment * market_caps[i] / (index_start_prices[i] * sum_market_caps)
                             for i in index_members}
                logging.debug(f"portfolio = {portfolio}")
                self.portfolios[index_name] = portfolio

    def start_prices(self, dfs, index_members, value_date):
        index_prices = {}
        for member_symbol in index_members:
            df = dfs[(dfs.symbol == member_symbol) & (dfs.date == value_date)]
            index_prices[member_symbol] = df["close"].values[0]
        return index_prices

    def get_portfolio(self, index_name):
        return self.portfolios[index_name]

    def get_portfolio_value(self, index_name, dfs, value_date):
        portfolio = self.portfolios[index_name]
        value = 0
        for member_symbol in portfolio:
            df = dfs[(dfs.symbol == member_symbol) & (dfs.date == value_date)]
            value += portfolio[member_symbol] * df["close"].values[0]
        logging.info(f"Index: {index_name} has value of Value = {value}")
        return value

    def get_comparison_dataframe(self, index_name, dfs, comparison,
                                 start_date, end_date):
        logging.debug(f"index_name = {index_name}, comparison = {comparison}")
        logging.debug(f"start_date = {start_date}, end_date = {end_date}")
        date_index = pd.date_range(start_date, end_date, freq=BDay())
        portfolio = self.portfolios[index_name]
        logging.debug(f"portfolio = {portfolio}")
        comp_key = list(comparison.keys())[0]
        comp_value = list(comparison.values())[0]
        logging.debug(f"comp_key = {comp_key}, comp_value = {comp_value}")
        timeseries = {x.date().strftime("%Y-%m-%d"): [0.0, 0.0] for x in date_index}
        logging.debug(f"length of timeseries = {len(timeseries)}")

        for member_symbol in portfolio:
            for i, value_date in enumerate(date_index):
                vd = value_date.date().strftime("%Y-%m-%d")
                try:
                    timeseries[vd][0] += dfs[(dfs.symbol == member_symbol) & (dfs.date == vd)]["close"].values[0] * portfolio[member_symbol]
                except (IndexError, KeyError) as e:
                    logging.warning(f"key error for {member_symbol} at {vd} -- skipping")
        for i, value_date in enumerate(date_index):
            vd = value_date.date().strftime("%Y-%m-%d")
            try:
                timeseries[vd][1] = dfs[(dfs.symbol == comp_key) & (dfs.date == vd)]["close"].values[0] * comp_value
            except (IndexError, KeyError) as e:
                logging.warning(f"key error for {comp_key} at {vd} -- skipping")

        df = pd.DataFrame.from_dict(timeseries, orient="index", columns=[index_name, comp_key])
        return df.loc[(df != 0).any(axis=1)]  # Remove rows with all zeros

    def plot_quotes(self, df, filename=COMPARE_INDEX_FILE):
        with PdfPages(filename) as pdf:
            logging.info("plotting {} dataframes".format(len(df)))
            fig = df.plot(figsize=[13, 8]).get_figure()
            pdf.savefig(fig)
            plt.close()
