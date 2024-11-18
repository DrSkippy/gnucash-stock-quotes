#!/usr/bin/env python3

from logging.config import dictConfig

from alphavantage.quotes import TickerQuotes
from indexes.asset_index import AssetIndex
from analyzer.gnucash import Gnucash

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
    res = tq.fetch_quotes()  # fetch the quotes from alphavantage
    tq.save_quotes(res)  # save quotes json
    dfs = tq.make_dataframes(res)  # transform quotes to pandas dataframes
    gnu = Gnucash(dfs)  # create gnucash object

    ai = AssetIndex()
    ai.set_up_indexes(dfs, "2024-07-12")
    a = ai.get_portfolio("equal_weight_price_index")
    b = ai.get_portfolio("constant_index")
    print(ai.get_portfolio_value("equal_weight_price_index", dfs, "2024-09-25"))
    print(ai.get_portfolio_value("constant_index", dfs, "2024-09-25"))
    print(ai.get_portfolio_value("market_cap_index", dfs, "2024-09-25"))
    dfi = ai.get_comparison_dataframe("market_cap_index", dfs, {"FFIV": 59.4106},
                                      "2024-01-01", "2024-09-27")
    ai.plot_quotes(dfi, "market_cap_index.pdf")
