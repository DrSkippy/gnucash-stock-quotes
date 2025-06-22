#!/usr/bin/env -S poetry run python

import argparse
import logging
from logging.config import dictConfig

from alphavantage.quotes import TickerQuotes
from analyzer.plots import CorrelationsPlotter

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
    parser = argparse.ArgumentParser(
        description='Correlations between two tickers with timeseries plots and correlation plot. Example: poetry run python bin/correlation.py -s "FFIV" "CRWD"')
    parser.add_argument('-s', '--security',
                        action='append',
                        nargs="+",
                        dest='security',
                        help='2 security symbols')
    args = vars(parser.parse_args())
    symbols = args['security'][0] if args['security'] is not None else []
    logging.debug(f"args={args} symbols={symbols}")
    assert (len(symbols) == 2)

    tq = TickerQuotes()
    dfs = tq.read_quotes(symbols=symbols)
    logging.debug(f"data frame has {dfs.symbol.unique()}")

    comp = CorrelationsPlotter(dfs)  # create correlations plotter
    comp.plot_correlation(*symbols)  # plot quotes
