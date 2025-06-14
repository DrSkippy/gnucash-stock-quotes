#!/usr/bin/env -S poetry run python

from logging.config import dictConfig
from alphavantage.quotes import TickerQuotes

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
    tq = TickerQuotes()
    res = tq.fetch_quotes()  # fetch the quotes from alphavantage
    tq.save_quotes(res)  # save quotes json