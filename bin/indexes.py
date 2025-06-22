#!/usr/bin/env -S poetry run python

import logging
from logging.config import dictConfig

from alphavantage.quotes import TickerQuotes
from market_indexes.asset_index import AssetIndex

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


class PortfolioAnalyzer:
    EQUAL_WEIGHT_INDEX = "equal_weight_price_index"
    CONSTANT_INDEX = "constant_index"
    MARKET_CAP_INDEX = "market_cap_index"
    DEFAULT_PORTFOLIO_VALUE = 10000

    def __init__(self, portfolio_value=DEFAULT_PORTFOLIO_VALUE):
        self.portfolio_value = portfolio_value
        self.ticker_quotes = TickerQuotes()
        quote_data = self.ticker_quotes.read_quotes()
        self.quote_data = self.ticker_quotes.make_wide_dataframe(quote_data)
        self.asset_index = AssetIndex(self.quote_data, portfolio_value=self.portfolio_value)

    def log_portfolio_value(self, index_name):
        portfolio_value = self.asset_index.get_portfolio(index_name)
        logging.info(f"{index_name}: {portfolio_value}")
        return portfolio_value

    def analyze_and_plot(self, index_name, comparison_portfolio, output_path):
        comparison_data = self.asset_index.get_comparison_dataframe(
            index_name,
            comparison_portfolio
        )
        self.asset_index.plot_quotes(comparison_data, output_path)


def main():
    analyzer = PortfolioAnalyzer()

    # Analyze different portfolio types
    analyzer.log_portfolio_value(PortfolioAnalyzer.EQUAL_WEIGHT_INDEX)
    analyzer.log_portfolio_value(PortfolioAnalyzer.CONSTANT_INDEX)
    analyzer.log_portfolio_value(PortfolioAnalyzer.MARKET_CAP_INDEX)

    # Compare and plot market cap index
    analyzer.analyze_and_plot(
        PortfolioAnalyzer.EQUAL_WEIGHT_INDEX,
        comparison_portfolio={"FFIV": 0},
        output_path=f"./data/{PortfolioAnalyzer.EQUAL_WEIGHT_INDEX}_comparison.pdf"
    )


if __name__ == "__main__":
    main()
