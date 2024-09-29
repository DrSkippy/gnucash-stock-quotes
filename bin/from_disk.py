#!/usr/bin/env python3
import logging

from alphavantage.quotes import TickerQuotes

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(message)s')

if __name__ == "__main__":
    tq = TickerQuotes()
    res = tq.read_quotes()  # read quotes from disk
    dfs = tq.make_dataframes(res)  # transform quotes to pandas dataframes
    tq.plot_quotes(dfs)  # pdf of time series
    tq.save_gnucash_quotes(dfs)  # save the csv for import into gnucash
