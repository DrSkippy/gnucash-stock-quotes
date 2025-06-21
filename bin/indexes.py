#!/usr/bin/env -S poetry run python

from logging.config import dictConfig
import datetime

from alphavantage.quotes import TickerQuotes
from market_indexes.asset_index import AssetIndex
from analyzer.plots import CorrelationsPlotter, plot_quotes

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
    dfs = tq.read_quotes()  
    ai = AssetIndex(dfs, portfolio_value=10000)
    date_today = datetime.datetime.now()
    # date_ninety = date_today - datetime.timedelta(days=(12*7))  # 12 weeks ago
    date_ninety = datetime.datetime.strptime("2025-01-22", FMT)
    ai.set_up_indexes(date_ninety.strftime(FMT))
    a = ai.get_portfolio("equal_weight_price_index")
    b = ai.get_portfolio("constant_index")
    print(ai.get_portfolio_value("equal_weight_price_index", date_ninety.strftime(FMT)))
    print(ai.get_portfolio_value("constant_index", date_ninety.strftime(FMT)))
    print(ai.get_portfolio_value("market_cap_index", date_ninety.strftime(FMT)))
    dfi = ai.get_comparison_dataframe("market_cap_index",{"FFIV": 59.4106},
                                      date_ninety.strftime(FMT), date_today.strftime(FMT))
    print(dfi)
    ai.plot_quotes(dfi, "./data/market_cap_index.pdf")
