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
    res = tq.fetch_quotes()  # fetch the quotes from alphavantage
    tq.save_quotes(res)  # save quotes json
    dfs = tq.make_dataframes(res)  # transform quotes to pandas dataframes
    gnu = Gnucash(dfs)  # create gnucash object

    ai = AssetIndex()
    ai.set_up_indexes(dfs, date_ninety.strftime(FMT))
    a = ai.get_portfolio("equal_weight_price_index")
    b = ai.get_portfolio("constant_index")
    print(ai.get_portfolio_value("equal_weight_price_index", dfs, date_ninety.strftime(FMT)))
    print(ai.get_portfolio_value("constant_index", dfs, date_ninety.strftime(FMT)))
    print(ai.get_portfolio_value("market_cap_index", dfs, date_ninety.strftime(FMT)))
    dfi = ai.get_comparison_dataframe("market_cap_index", dfs, {"FFIV": 59.4106},
                                      date_ninety.strftime(FMT), date_today.strftime(FMT))
    ai.plot_quotes(dfi, "market_cap_index.pdf")
