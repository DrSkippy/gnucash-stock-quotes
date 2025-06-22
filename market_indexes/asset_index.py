from typing import Dict, List, Set, Union
import json
import logging
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pandas.tseries.offsets import *


class AssetIndex:
    """Manages and calculates various types of asset indexes and portfolios."""

    # File paths
    INDEX_FILE = "./indexes.json"
    COMPARE_INDEX_FILE = "./data/compare_index.pdf"


    def __init__(self, dfs: pd.DataFrame, portfolio_value: float = 10000, filename: str = INDEX_FILE):
        """
        Represents a class that initializes and manages data analysis and calculations
        for financial portfolios.

        This class processes dataframes containing financial data, loads configuration
        from a provided filename, and performs various setup operations such as
        verifying data completeness and initializing portfolios. It calculates
        financial indexes based on the provided data and configuration.

        :param dfs: Dataframe containing financial data for analysis and portfolio
            management.
        :type dfs: pd.DataFrame
        :param portfolio_value: Initial value of the portfolio. This value is used as
            the default total portfolio value.
        :type portfolio_value: float
        :param filename: The name of the file where the configuration is stored. This
            file specifies the indexes and symbols to be analyzed and managed.
        :type filename: str
        """
        self.portfolio_value = portfolio_value
        self.portfolios: Dict[str, Dict[str, float]] = {}

        self.config = self._load_config(filename)
        self.indexes_list = self.config["asset_indexes"]
        self.symbols_list = self._get_unique_symbols()

        self.dfs = self._prepare_dataframe(dfs)
        self._verify_data_completeness()
        self._initialize_portfolios()
        self._calculate_indexes()

    def _load_config(self, filename: str) -> dict:
        """
        Loads configuration data from a JSON file.

        This method reads a JSON file from the specified filename, parses its content,
        and logs the number of records read from the file. The parsed JSON content is
        returned as a dictionary.

        :param filename: Name of the JSON file to load configuration data from
        :type filename: str
        :return: A dictionary containing the parsed configuration data
        :rtype: dict
        """
        with open(filename, "r") as fin:
            config = json.load(fin)
            logging.info(f"Read {len(config)} records from {filename}")
            return config

    def _get_unique_symbols(self) -> List[str]:
        """
        Gets a list of unique symbols from the indexes_list attribute.

        This method iterates through each dictionary in the `indexes_list`, extracts
        the symbols from the "MEMBERS" key, and accumulates them in a set to ensure
        uniqueness. At the end of the process, the method logs the number of unique
        symbols found before returning them as a list.

        :return: A list of unique symbols extracted from the "MEMBERS" key across
            all dictionaries in the `indexes_list` attribute.
        :rtype: List[str]
        """
        symbols: Set[str] = set()
        for index in self.indexes_list:
            symbols.update(index["MEMBERS"])
        logging.info(f"Loaded {len(symbols)} unique symbols")
        return list(symbols)

    def _prepare_dataframe(self, dfs: pd.DataFrame) -> pd.DataFrame:
        """
        Prepares the DataFrame by retaining only the columns specified in the symbols_list attribute,
        dropping entirely empty columns, and logging descriptive statistics of the resulting DataFrame.

        :param dfs: The input DataFrame containing raw data to be processed.
        :type dfs: pd.DataFrame
        :return: A DataFrame with columns filtered by symbols_list and without
            columns that are entirely empty.
        :rtype: pd.DataFrame
        """
        df = dfs[self.symbols_list]
        df.dropna(axis=1, how="all", inplace=True)
        logging.info(f"DataFrame stats:\n{df.describe()}")
        return df.copy()

    def _verify_data_completeness(self) -> None:
        """
        Verifies the completeness of data by checking for any symbols in the symbol list
        that are not present as columns in the data frame. Logs a warning if any symbols
        are found to be missing.

        :return: None
        """
        missing_symbols = [sym for sym in self.symbols_list if sym not in self.dfs.columns]
        if missing_symbols:
            logging.warning(f"Missing price data for symbols: {missing_symbols}")

    def _initialize_portfolios(self) -> None:
        """
        Initializes portfolios based on the list of indexes provided and appropriate
        calculation methods. It determines the type of portfolio calculator to use
        (EQUAL_WEIGHT, CONSTANT_WEIGHT, or MARKET_CAP_WEIGHT) for each index and
        invokes it to calculate and store the portfolio data. The portfolio will
        be calculated starting from the provided "CREATED_DATE", or the earliest
        available date if not specified.

        :raises KeyError: If the index dictionary does not have a 'NAME' key.
        :raises ValueError: If an invalid index portfolio type is encountered.

        :rtype: None
        """
        portfolio_calculators = {
            "EQUAL_WEIGHT": self._calculate_equal_weight_portfolio,
            "CONSTANT": self._calculate_constant_weight_portfolio,
            "MARKET_CAP": self._calculate_market_cap_portfolio
        }

        for idx in self.indexes_list:
            index_name = idx["NAME"]
            index_type = idx["TYPE"]
            calculator = portfolio_calculators.get(index_type)
            if calculator:
                start_date = idx.get("CREATED_DATE", self.dfs.index.min())
                self.portfolios[index_name] = calculator(idx, start_date)
                logging.info(f"Initialized {index_name} portfolio")

    def _calculate_equal_weight_portfolio(self, index_config: dict, start_date: str) -> Dict[str, float]:
        """
        Calculates the equal weight allocation for a portfolio based on the provided index
        configuration and starting date. The method assumes the portfolio is distributed
        equally among all members of the index. The allocation is calculated as the total
        portfolio value divided evenly among all index members, weighted by their starting prices.

        :param index_config: A dictionary containing index configuration data. The key "MEMBERS"
                             should map to a list of symbols representing members of the index.
        :param start_date: Starting date as a string from which to fetch the asset prices.
        :return: A dictionary where the keys are the asset symbols and the values represent
                 the calculated weight allocation for each asset.
        :rtype: Dict[str, float]
        """
        members = index_config["MEMBERS"]
        start_prices = self.dfs.loc[start_date, members]
        return {symbol: self.portfolio_value / (len(members) * price)
                for symbol, price in start_prices.items()}

    def _calculate_constant_weight_portfolio(self, index_config: dict, start_date: str) -> Dict[str, float]:
        """
        Calculates the constant weight portfolio based on the given index configuration and
        start date. The method determines the proportional weights of members in a
        portfolio such that the total portfolio value is allocated consistently by the
        initial weights, derived from the start prices.

        :param index_config: A dictionary containing the configuration of the index,
            including member details. The "MEMBERS" key should contain a list of asset
            symbols representing the portfolio members.
        :param start_date: The starting date in string format for retrieving the
            prices of the members in the portfolio from the dataframe.
        :return: A dictionary mapping each member symbol to its associated weight in
            the portfolio, expressed as the proportion of the portfolio value attributed
            to each member based on the start prices.
        :rtype: Dict[str, float]
        """
        members = index_config["MEMBERS"]
        start_prices = self.dfs.loc[start_date, members]
        total_price = start_prices.sum()
        return {symbol: self.portfolio_value / total_price for symbol in members}

    def _calculate_market_cap_portfolio(self, index_config: dict, start_date: str) -> Dict[str, float]:
        """
        Calculates the market capitalization-based portfolio allocation for a given
        list of members and their respective market capitalizations on a given start
        date.

        This function determines the weight of each portfolio member based on their
        market capitalization relative to the total market capitalization, and adjusts
        the allocation accordingly based on the portfolio value and the start prices.

        :param index_config: Dictionary containing configuration details for the index,
            including "MEMBERS" (list of portfolio members) and "MARKET_CAP"
            (list of their corresponding market capitalizations).
        :type index_config: dict

        :param start_date: The date from which the market capitalization portfolio
            allocation is calculated.
        :type start_date: str

        :return: A dictionary where keys are portfolio member symbols and values are
            their calculated allocations.
        :rtype: Dict[str, float]
        """
        members = index_config["MEMBERS"]
        market_caps = dict(zip(members, index_config["MARKET_CAP"]))
        start_prices = self.dfs.loc[start_date, members]
        total_mcap = sum(index_config["MARKET_CAP"])

        return {symbol: self.portfolio_value * market_caps[symbol] /
                        (price * total_mcap) for symbol, price in start_prices.items()}

    def print_indexes(self):
        """
        Print indexes and their associated ticker members in a structured format.

        This method iterates over the ``indexes_list`` attribute, which contains
        information about indexes. For each index, it prints the index name along
        with its corresponding tickers in a hierarchical view. The output is
        formatted with specific prefixes to depict the tree structure.

        :raises AttributeError: If the ``indexes_list`` attribute does not exist
            in the instance.
        """
        print("Indexes:")
        for count, idx in enumerate(self.indexes_list):
            is_last_index = count == len(self.indexes_list) - 1
            index_prefix = "└──" if is_last_index else "├──"
            print(f"{index_prefix} {idx['NAME']}")

            # Print tickers for this market
            for i, ticker in enumerate(idx['MEMBERS']):
                is_last_ticker = i == len(idx['MEMBERS']) - 1
                ticker_prefix = "    └──" if is_last_ticker else "    ├──"
                if not is_last_index:
                    ticker_prefix = ticker_prefix.replace("    ", "│   ")
                print(f"{ticker_prefix} {ticker}")

    def get_portfolio(self, index_name: str) -> Dict[str, float]:
        """
        Retrieves the portfolio data for the specified index.

        This function allows access to portfolio data stored under a particular index
        name. The portfolios are represented as dictionaries containing the index data.

        :param index_name: The name of the portfolio index to retrieve.
        :type index_name: str
        :return: A dictionary representing the portfolio data for the given index.
        :rtype: Dict[str, float]
        """
        return self.portfolios[index_name]

    def _calculate_indexes(self) -> None:
        """
        Calculates index values for each portfolio and updates the corresponding
        dataframes in the `dfs` dictionary. The calculation is based on the
        weighted sum of shares for each symbol in a portfolio.

        :raises KeyError: If a symbol in the portfolio is not found in the `dfs`
            dictionary.
        :raises TypeError: If the values in `portfolio` cannot be multiplied with
            the corresponding dataframes in `dfs`.

        :return: None
        """
        for index_name, portfolio in self.portfolios.items():
            self.dfs[index_name] = sum(self.dfs[symbol] * shares
                                       for symbol, shares in portfolio.items())
            logging.info(f"Calculated {index_name} index values")

    def get_comparison_dataframe(self, index_name: str,
                                 comparison_portfolio: Dict[str, float]) -> pd.DataFrame:
        """
        Generates a comparison DataFrame containing data for the specified index
        and a comparison portfolio. It adjusts the comparison portfolio based on
        the provided holdings or calculates the holdings to match the portfolio's value.

        :param index_name: Name of the index to be compared.
        :type index_name: str
        :param comparison_portfolio: A dictionary containing a single stock symbol as a key
            and the number of shares or 0 as the value. If 0 is provided, the method
            calculates the shares needed to match the portfolio value.
        :type comparison_portfolio: Dict[str, float]
        :return: A DataFrame containing the index data and the calculated comparison
            portfolio data, indexed by date and sorted.
        :rtype: pd.DataFrame
        """
        symbol = next(iter(comparison_portfolio))
        shares = next(iter(comparison_portfolio.values()))

        if shares == 0:
            start_date = next(idx["CREATED_DATE"] for idx in self.indexes_list
                              if idx["NAME"] == index_name)
            shares = self.portfolio_value / self.dfs.loc[start_date, symbol]

        comparison_name = f"{symbol}_comparison"
        self.dfs[comparison_name] = self.dfs[symbol] * shares

        return self.dfs[[index_name, comparison_name]].dropna().sort_index()

    def plot_quotes(self, df: pd.DataFrame, filename: str = COMPARE_INDEX_FILE) -> None:
        """
        Generate a PDF with plot visualization for given DataFrame.

        This method takes a pandas DataFrame as input, creates a visualization
        of its data, and saves it as a multi-page PDF file to the specified
        filename. The plot is formatted with default figure dimensions.

        :param df: The pandas DataFrame containing data to be visualized.
        :type df: pd.DataFrame
        :param filename: The path and filename where the PDF will be saved.
                         Defaults to COMPARE_INDEX_FILE.
        :type filename: str, optional
        :return: None
        """
        with PdfPages(filename) as pdf:
            fig = df.plot(figsize=[10, 5]).get_figure()
            pdf.savefig(fig)
            plt.close()
