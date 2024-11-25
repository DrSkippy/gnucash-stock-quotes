#!/usr/bin/env python3
import argparse

from alphavantage.quotes import TickerQuotes
from analyzer.gnucash import Gnucash
from analyzer.correlations import Compare

import logging
from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s %(funcName)s at %(lineno)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'formatter': 'default'
    }},
    'root': {
        'level': 'DEBUG',
        'handlers': ['wsgi']
    }
})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Correlations between two tickers with timeseries plots and correlation plot. Example: poetry run python bin/correlation.py -s "FFIV" "CRWD"')
    parser.add_argument('-c', '--crypto',
                        action='append',
                        nargs="+",
                        dest='crypto',
                        help='2, 1 or zero cryto currency symbols')
    parser.add_argument('-s', '--security',
                        action='append',
                        nargs="+",
                        dest='security',
                        help='2, 1 or zero security symbols')
    args = vars(parser.parse_args())
    symbols = []
    tickers = {
        "DIGITAL_CURRENCY_DAILY": [],
        "TIME_SERIES_DAILY": []
    }
    if args['crypto'] is not None:
        symbols += args['crypto'][0]
        tickers["DIGITAL_CURRENCY_DAILY"] = args['crypto'][0]
    if args['security'] is not None:
        symbols += args['security'][0]
        tickers["TIME_SERIES_DAILY"] = args['security'][0]
    logging.debug(f"args={args} symbols={symbols}")
    assert (len(symbols) == 2)
    logging.debug(f"tickers={tickers}")
    tq = TickerQuotes(tickers=tickers)
    res = tq.fetch_quotes()  # fetch the quotes from alphavantage
    tq.save_quotes(res)  # save quotes json
    dfs = tq.make_dataframes(res)  # transform quotes to pandas dataframes
    comp = Compare(dfs)
    comp.plot_quotes(dfs, *symbols)  # plot quotes
