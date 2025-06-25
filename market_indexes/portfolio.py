import logging

import pandas as pd
from analyzer.plots import CorrelationsPlotter

from alphavantage.quotes import TickerQuotes
from market_indexes.asset_index import AssetIndex


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

    def correlations_plot(self, symbols, start_date=None):
        """
        Generates a correlation plot for the specified symbols, optionally starting from a given date.

        :param symbols: List of security symbols to analyze.
        :type symbols: list
        :param start_date: Optional start date for the analysis in YYYY-MM-DD format.
        :type start_date: str | None
        """
        if start_date:
            dfs = self.asset_index.dfs[self.asset_index.dfs.index >= start_date]
        else:
            dfs = self.asset_index.dfs
            logging.info(f"symbols={symbols}")
            logging.info(f"data frame has {dfs.columns}")

        comp = CorrelationsPlotter(dfs)
        comp.plot_correlation(*symbols)
