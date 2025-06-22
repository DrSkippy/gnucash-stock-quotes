#!/usr/bin/env -S poetry run python

import argparse
import logging
from logging.config import dictConfig

from alphavantage.quotes import TickerQuotes
from analyzer.gnucash import Gnucash
from analyzer.plots import CorrelationsPlotter
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
    DEFAULT_PORTFOLIO_VALUE = 10000

    def __init__(self, portfolio_value=DEFAULT_PORTFOLIO_VALUE):
        """
        Initializes a new instance of the class responsible for managing portfolio value and financial
        quote data. This class sets up the financial data structures required to handle wide-format
        quote data and asset indexing based on the provided portfolio value or the default portfolio
        value.

        :param portfolio_value: The initial value of the portfolio used for calculations and asset
            indexing. If not explicitly provided, a default is used.
        :type portfolio_value: float
        """
        self.portfolio_value = portfolio_value
        self.ticker_quotes = TickerQuotes()
        quote_data = self.ticker_quotes.read_quotes()
        self.quote_data = self.ticker_quotes.make_wide_dataframe(quote_data)
        self.asset_index = AssetIndex(self.quote_data, portfolio_value=self.portfolio_value)

    def log_portfolio_value(self, index_name):
        """
        Logs the portfolio value for the given index and returns the value.

        The method retrieves the portfolio value associated with the provided index
        name from the asset index. It then logs the value and returns the retrieved
        portfolio value.

        :param index_name: Name of the index whose portfolio value is to be logged.
                           Used to identify the portfolio within the asset index.

        :return: The retrieved portfolio value corresponding to the provided index name.
        :rtype: float | int
        """
        portfolio_value = self.asset_index.get_portfolio(index_name)
        logging.info(f"{index_name}: {portfolio_value}")
        return portfolio_value

    def analyze_and_plot(self, index_name, comparison_portfolio, output_path):
        """
        Analyzes the comparison between a specified index and a given portfolio,
        then generates and saves the corresponding plot to the output path. This
        function utilizes the asset_index attribute to retrieve the necessary data
        and perform the plotting.

        :param index_name: Name of the index to be analyzed.
        :type index_name: str
        :param comparison_portfolio: The portfolio to compare against the index.
        :type comparison_portfolio: str
        :param output_path: File path where the output plot will be saved.
        :type output_path: str
        :return: None
        """
        comparison_data = self.asset_index.get_comparison_dataframe(
            index_name,
            comparison_portfolio
        )
        self.asset_index.plot_quotes(comparison_data, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""**Save Haven Adventure Kit** (SHaK) is a tool for analyzing and plotting stock market data.
        It allows you to compare two securities, create a gnucash quotes file, or analyze market indexes.
        """)
    parser.add_argument("command",
                        choices=['compare', 'gnucash', 'index'],
                        help="Command to execute: 'compare' for comparing securities, 'gnucash' for creating a gnucash quotes file, or 'index' for analyzing market indexes."
                        )
    parser.add_argument('-c', '--compare-securities',
                        action='append',
                        nargs="+",
                        dest='security',
                        help='2 security symbols')
    parser.add_argument('-l', '--list',
                        action='store_true',
                        default=False,
                        help='List available securities in the database')
    parser.add_argument('-i', '--index-name',
                        default=None,
                        help='Name of the index to analyze (e.g., "equal_weight", "constant", "market_cap")')
    parser.add_argument('-s', '--start-date',
                        default=None,
                        help='Start date for the analysis in YYYY-MM-DD format')
    parser.add_argument('-p', '--compare-portfolio',
                        action='append',
                        nargs="+",
                        dest='comp_portfolio',
                        help='Portfolio to compare against the index, e.g., "FFIV 0" for default allocation to FFIV')

    args = vars(parser.parse_args())

    if args['command'] == 'compare':
        if args['list']:
            tq = TickerQuotes()
            tq.print_tickers()

        if len(args['security'][0]) == 2:
            symbols = args['security'][0] if args['security'] is not None else []
            logging.info(f"args={args} symbols={symbols}")
            tq = TickerQuotes()
            dfs = tq.read_quotes(symbols=symbols)
            logging.info(f"data frame has {dfs.symbol.unique()}")

            comp = CorrelationsPlotter(dfs)
            comp.plot_correlation(*symbols)
    elif args['command'] == 'gnucash':
        dfs = TickerQuotes().read_quotes()  # save quotes json
        Gnucash(dfs).process_quotes()  # create gnucash object
    elif args['command'] == 'index':
        analyzer = PortfolioAnalyzer()
        if args['list']:
            tq = TickerQuotes()
            tq.print_tickers()
            analyzer.asset_index.print_indexes()
        if args['index_name']:
            if args['comp_portfolio'] is not None and len(args['comp_portfolio'][0]) == 2:
                cp = {str(args['comp_portfolio'][0][0]): float(args['comp_portfolio'][0][1])}
            else:
                cp = {"FFIV": 0}
            logging.info(f"comparison portfolio={cp}")
            index_name = args['index_name']
            analyzer.log_portfolio_value(index_name)
            # Compare and plot market cap index
            analyzer.analyze_and_plot(
                index_name,
                comparison_portfolio=cp,
                output_path=f"./data/{index_name}_comparison.pdf"
            )
