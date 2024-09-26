import json
import logging

class AssetIndex():

    def __init__(self, filename="./tickers.json"):
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
                portfolio = {i:investment / sum_of_prices for i in index_members}
                logging.debug(f"portfolio = {portfolio}")
                self.portfolios[index_name] = portfolio
            elif index_name == "market_cap_index":
                market_caps = dict(zip(i["MEMBERS"], i["MARKET_CAP_2024-09-25"]))
                sum_market_caps = sum(i["MARKET_CAP_2024-09-25"])
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
        for m in portfolio:
            for df in dfs:
                if m in df.symbol[0]:
                    break
            value += portfolio[m] * df.loc[value_date, "close"]
        return value