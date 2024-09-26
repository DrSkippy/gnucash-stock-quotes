#!/usr/bin/env python3
import logging

from alphavantage.quotes import TickerQuotes
from indexes.asset_index import AssetIndex

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
    tq = TickerQuotes()
    res = tq.fetch_quotes()          # fetch the quotes from alphavantage
    tq.save_quotes(res)              # save quotes json
    dfs = tq.make_dataframes(res)    # transform quotes to pandas dataframes
    tq.plot_quotes(dfs)              # pdf of time series
    tq.save_gnucash_quotes(dfs)      # save the csv for import into gnucash

    ai = AssetIndex()
    ai.set_up_indexes(dfs, "2024-05-03")
    a = ai.get_portfolio("equal_weight_price_index")
    b = ai.get_portfolio("constant_index")
    print(ai.get_portfolio_value("equal_weight_price_index", dfs, "2024-09-25"))
    print(ai.get_portfolio_value("constant_index", dfs, "2024-09-25"))
    print(ai.get_portfolio_value("market_cap_index", dfs, "2024-09-25"))




