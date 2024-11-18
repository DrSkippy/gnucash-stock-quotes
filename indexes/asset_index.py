import json
import logging

import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pandas.tseries.offsets import *


class AssetIndex():

    def __init__(self, filename="./indexes.json"):
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
        for m in index_members:
            for df in dfs:
                logging.debug(f"looking for {m} in price data {df.head(1)}")
                if m in df.symbol[0]:
                    break
            start_price = df.loc[value_date, "close"]
            index_prices[m] = start_price
        return index_prices

    def get_portfolio(self, index_name):
        return self.portfolios[index_name]

    def get_portfolio_value(self, index_name, dfs, value_date):
        portfolio = self.portfolios[index_name]
        value = 0
        for member_symbol in portfolio:
            for df in dfs:
                if member_symbol in df.symbol[0]:
                    break
            value += portfolio[member_symbol] * df.loc[value_date, "close"]
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
            for df in dfs:
                if member_symbol in df.symbol[0]:
                    for i, value_date in enumerate(date_index):
                        vd = value_date.date().strftime("%Y-%m-%d")
                        try:
                            timeseries[vd][0] += df.loc[vd, "close"] * portfolio[member_symbol]
                        except KeyError as e:
                            logging.warning(f"key error for {member_symbol} at {vd} -- skipping")
                    continue
        for df in dfs:
            if comp_key in df.symbol[0]:
                for i, value_date in enumerate(date_index):
                    vd = value_date.date().strftime("%Y-%m-%d")
                    try:
                        timeseries[vd][1] = df.loc[vd, "close"] * comp_value
                    except KeyError as e:
                        logging.warning(f"key error for {member_symbol} at {vd} -- skipping")
                break
        df = pd.DataFrame.from_dict(timeseries, orient="index", columns=[index_name, comp_key])
        return df.loc[(df != 0).any(axis=1)]  # Remove rows with all zeros

    def plot_quotes(self, dfs, filename="./compare_index.pdf"):
        with PdfPages(filename) as pdf:
            logging.info("plotting {} dataframes".format(len(dfs)))
            fig = dfs.plot(figsize=[13, 8]).get_figure()
            pdf.savefig(fig)
            plt.close()
