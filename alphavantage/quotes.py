#!/usr/bin/env -S poetry run python

import json
import logging
import time

import pandas as pd
import requests
from alphavantage.db_utils import QuoteDatabase


class TickerQuotes:
  
    HIGH_LOW_CLOSE_VOLUME_ = ["open", "high", "low", "close", "volume"]
    TAG_STOCKS_ = "2. Symbol"
    TAG_CRYPTO_ = "2. Digital Currency Code"
    KEY_STOCKS_ = "Time Series (Daily)"
    KEY_CRYPTO_ = "Time Series (Digital Currency Daily)"
    KEY_META_DATA_ = "Meta Data"
    ERROR_MESSAGE_ = "Error Message"
    RATE_DELAY = 0  # for free tier 11 sec delay between requests
    TICKERS_FILE = "./tickers.json"
    QUOTES_FILE = "./data/quotes.json"

    def __init__(self, filename=TICKERS_FILE, tickers=None):
        with open(filename, "r") as fin:
            config = json.load(fin)
            logging.info(f"read from {filename}: {len(config)} records")
        self.key = config["configuration"]["key"]
        self.url_keys = config["configuration"]["url_base"].keys()
        url_keys_test = config["tickers"].keys()
        assert (self.url_keys == url_keys_test)
        self.url_base = config["configuration"]["url_base"]
        if tickers is None:
            self.tickers = config["tickers"]
        else:
            self.tickers = tickers
        self.db = QuoteDatabase(config)
        self.db.create_tables()

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
        if self.KEY_META_DATA_ not in t_dict:
            logging.error(f"Error: {t_dict.keys()}")
            return None, None

        if self.ERROR_MESSAGE_ in t_dict:
            logging.error(f"Error: {t_dict[self.ERROR_MESSAGE_]}")
            return None, None

        if self.TAG_STOCKS_ in t_dict[self.KEY_META_DATA_]:
            symbol = t_dict[self.KEY_META_DATA_][self.TAG_STOCKS_]
            logging.info(f"Processing {symbol} as stocks")
            df = pd.DataFrame().from_dict(t_dict[self.KEY_STOCKS_], orient="index")
        elif self.TAG_CRYPTO_ in t_dict[self.KEY_META_DATA_]:
            symbol = t_dict[self.KEY_META_DATA_][self.TAG_CRYPTO_]
            logging.info(f"Processing {symbol} as crypto")
            df = pd.DataFrame().from_dict(t_dict[self.KEY_CRYPTO_], orient="index")
        else:
            logging.error(f"Error: {t_dict[self.KEY_META_DATA_].keys()}")
            return None, None

        df.columns = self.HIGH_LOW_CLOSE_VOLUME_
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
                logging.info('Getting ticker = {}'.format(t))
                url = self.url_base[key].format(t, self.key)
                logging.info('url = {}'.format(url))
                res = requests.get(url)
                logging.info('resp = {}'.format(res))
                res_json = res.json()
                results.append(res_json)
                logging.info(f"Waiting {self.RATE_DELAY} sec...")
                time.sleep(self.RATE_DELAY)
        return results

    def save_quotes(self, results, filename=QUOTES_FILE):
        """Save quotes to both JSON file and database"""
        # Save to JSON file
        with open(filename, "w") as fout:
            logging.info("writing {} records...".format(len(results)))
            fout.write(json.dumps(results))
        
        # Save to database
        dfs = self.make_dataframes(results)
        for df in dfs:
            self.db.save_quotes(df)

    def read_quotes(self, filename=None, start_date=None, end_date=None, symbols=None):
        """Read quotes from either JSON file or database"""
        if filename:
            # Use JSON file for full dataset
            with open(filename, "r") as fin:
                results = json.load(fin)
            logging.info("read {} records...".format(len(results)))
            return self.make_dataframes(results)
        else:
            # Use database for filtered queries
            return self.db.read_quotes(start_date, end_date, symbols)

    def make_dataframes(self, results):
        dfs = []
        for q in results:
            df, symbol = self._process_record(q)
            if df is None:
                logging.error(f"Error skipping processing record for {q.get(self.KEY_META_DATA_, {}).get(self.TAG_STOCKS_, 'Unknown')} due to error. See logs for details.")
                continue
            df = df.sort_index()
            dfs.append(df[["namespace", "symbol", "close", "currency"]][(df.index > '2016-01-01')])
        return dfs

    def __del__(self):
        """Cleanup database connection"""
        if hasattr(self, 'db'):
            self.db.close()

if __name__ == "__main__":
    from logging.config import dictConfig

    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s %(funcName)s at %(lineno)s: %(message)s',
        }},
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': 'ext://sys.stdout'
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        }
    })
    
    logging.info("starting")
    tq = TickerQuotes()
    results = tq.fetch_quotes()
    tq.save_quotes(results)
    dfs = tq.make_dataframes(results)
    logging.info(dfs)