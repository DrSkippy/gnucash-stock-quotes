#!/usr/bin/env python3
import requests
import time 
import json
import logging

import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(message)s')


class TickerQuotes:

    def __init__(self, filename="tickers.json"):
        with open("./tickers.json", "r") as fin:
            config = json.load(fin)
        self.key = config["configuration"]["key"]
        self.url_base = config["configuration"]["url_base"]
        self.tickers, self.ticker_namespaces = self._ticker_list(config["tickers"])

    def _ticker_list(self, d):
        tic_res = []
        tic_map = {}
        for k, v in d.items():
            for i in v:
                tic_res.append(i)
                tic_map[i] = k
        return tic_res, tic_map

    def _process_record(self, t_dict):
        symbol = t_dict["Meta Data"]["2. Symbol"]
        df = pd.DataFrame().from_dict(t_dict["Weekly Time Series"], orient="index")
        df.columns = ["open","high", "low", "close", "volume"]
        df.open = df.open.astype(float).fillna(0.0)
        df.high = df.high.astype(float).fillna(0.0)
        df.low = df.low.astype(float).fillna(0.0)
        df.close = df.close.astype(float).fillna(0.0)
        df.volume = df.volume.astype(float).fillna(0.0)
        df["symbol"] = symbol
        df["currency"] = "USD"
        df["namespace"] = self.ticker_namespaces[symbol]
        logging.info(df.head())
        return df, symbol

    def fetch_quotes(self):
        results = []
        for t in self.tickers:
            logging.info('getting ticker = {}'.format(t))
            url = self.url_base.format(t, self.key)
            logging.info('url = {}'.format(url))
            res = requests.get(url)
            logging.info('resp = {}'.format(res))
            res_json = res.json()
            if "Weekly Time Series" in res_json:
                results.append(res_json)
            else:
                logging.error("{} failed with message {}".format(t, res_json))
            logging.info("waiting 11 sec...")
            time.sleep(11)
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

    def plot_quotes(self, dfs, filename="./quotes.pdf"):
        with PdfPages(filename) as pdf:
            logging.info("plotting {} dataframes".format(len(dfs)))
            for df in dfs:
                symbol = df.symbol[0].strip()
                logging.info("  plotting symbol={} len={}".format(symbol, len(df.close)))
                fig = df.plot(y="close", figsize=[13, 5], title="ticker={}".format(symbol)).get_figure()
                pdf.savefig(fig)
            plt.close()

    def make_dataframes(self, results):
        dfs = []
        for q in results:
            df, symbol = self._process_record(q)
            df = df.sort_index()
            dfs.append(df[["namespace", "symbol", "close", "currency"]][(df.index > '2016-01-01')])
        return dfs

    def save_gnucash_quotes(self, dfs, filename="./data/prices.csv"):
        df_out = pd.concat(dfs)
        df_out.to_csv(filename, header=False)
