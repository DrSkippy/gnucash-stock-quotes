#!/usr/bin/env -S poetry run python

from logging.config import dictConfig
import datetime

from alphavantage.quotes import TickerQuotes
from indexes.asset_index import AssetIndex
from analyzer.gnucash import Gnucash
from analyzer.correlations import Compare

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

FMT = "%Y-%m-%d"

if __name__ == "__main__":
    date_today = datetime.datetime.now()
    date_ninety = date_today - datetime.timedelta(days=12*7-2)
    tq = TickerQuotes()
    dfs = tq.read_quotes()  # save quotes json
    gnu = Gnucash(dfs)  # create gnucash object

