#!/usr/bin/env python3
import json
import logging
import time

import pandas as pd
import requests

HIGH_LOW_CLOSE_VOLUME_ = ["open", "high", "low", "close", "volume"]
TAG_STOCKS_ = "2. Symbol"
TAG_CRYPTO_ = "2. Digital Currency Code"
KEY_STOCKS_ = "Time Series (Daily)"
KEY_CRYPTO_ = "Time Series (Digital Currency Daily)"
KEY_META_DATA_ = "Meta Data"


class TickerQuotes:
    RATE_DELAY = 0  # for free tier 11 sec delay between requests

    def __init__(self, filename="./tickers.json"):
        with open(filename, "r") as fin:
            config = json.load(fin)
            logging.info(f"read from {filename}: {len(config)} records")
        self.key = config["configuration"]["key"]
        self.url_keys = config["configuration"]["url_base"].keys()
        url_keys_test = config["tickers"].keys()
        assert (self.url_keys == url_keys_test)
        self.url_base = config["configuration"]["url_base"]
        self.tickers = config["tickers"]

    def _process_record(self, t_dict):
        """
        {'Meta Data':
          {'1. Information': 'Daily Prices (open, high, low, close) and Volumes',
           '2. Symbol': 'NASDX',
           '3. Last Refreshed': '2024-09-19',
           '4. Output Size': 'Compact',
           '5. Time Zone': 'US/Eastern'},
           'Time Series (Daily)':
              {'2024-09-19':
                 {'1. open': '39.9000',
                 '2. high': '39.9000',
                 '3. low': '39.9000',
                 '4. close': '39.9000',
                 '5. volume': '0'},
              ...
        """

        if TAG_STOCKS_ in t_dict[KEY_META_DATA_]:
            symbol = t_dict[KEY_META_DATA_][TAG_STOCKS_]
            logging.info(f"processing {symbol} as stocks")
            df = pd.DataFrame().from_dict(t_dict[KEY_STOCKS_], orient="index")
        elif TAG_CRYPTO_ in t_dict[KEY_META_DATA_]:
            symbol = t_dict[KEY_META_DATA_][TAG_CRYPTO_]
            logging.info(f"processing {symbol} as crypto")
            df = pd.DataFrame().from_dict(t_dict[KEY_CRYPTO_], orient="index")
        else:
            logging.error(f"error: {t_dict[KEY_META_DATA_].keys()}")
            return None, None

        df.columns = HIGH_LOW_CLOSE_VOLUME_
        df.open = df.open.astype(float).fillna(0.0)
        df.high = df.high.astype(float).fillna(0.0)
        df.low = df.low.astype(float).fillna(0.0)
        df.close = df.close.astype(float).fillna(0.0)
        df.volume = df.volume.astype(float).fillna(0.0)
        df["symbol"] = symbol
        df["currency"] = "USD"
        df["namespace"] = "NASDAQ"
        logging.info(df.head())
        return df, symbol

    def fetch_quotes(self):
        results = []
        for key in self.url_keys:
            for t in self.tickers[key]:
                logging.info('getting ticker = {}'.format(t))
                url = self.url_base[key].format(t, self.key)
                logging.info('url = {}'.format(url))
                res = requests.get(url)
                logging.info('resp = {}'.format(res))
                res_json = res.json()
                results.append(res_json)
                logging.info(f"waiting {self.RATE_DELAY} sec...")
                time.sleep(self.RATE_DELAY)
        return results

    def save_quotes(self, results, filename="./data/quotes.json"):
        with open(filename, "w") as fout:
            logging.info("writing {} records...".format(len(results)))
            fout.write(json.dumps(results))

    def read_quotes(selfs, filename="./data/quotes.json"):
        with open(filename, "r") as fin:
            results = json.load(fin)
        logging.info("read {} records...".format(len(results)))
        return results

    def make_dataframes(self, results):
        dfs = []
        for q in results:
            df, symbol = self._process_record(q)
            df = df.sort_index()
            dfs.append(df[["namespace", "symbol", "close", "currency"]][(df.index > '2016-01-01')])
        return dfs
