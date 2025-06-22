import pandas as pd
from typing import Union, List
from analyzer.plots import plot_stock_prices


class Gnucash:
    def __init__(self, dataframes: Union[pd.DataFrame, List[pd.DataFrame]], prices_file: str = "./data/prices.csv"):
        """
        Initialize Gnucash with dataframes and output file path.
        
        Args:
            dataframes: Single dataframe or list of dataframes to process
            prices_file: Path to save the processed data
        """
        self.prices_file = prices_file
        self.dataframe = dataframes

    def process_quotes(self) -> None:
        """
        Processes stock quote data and carries out required operations that include
        plotting stock prices and saving quotes in GnuCash format. This method is
        responsible for invoking operations defined elsewhere in the application that
        handle specific aspects of stock data processing.

        :return: None
        """
        plot_stock_prices(self.dataframe)
        self.save_gnucash_quotes()

    def save_gnucash_quotes(self) -> None:
        """
        Saves GnuCash quotes contained in the dataframe to a CSV file without including the header.

        This method uses the path specified by `prices_file` to save the
        data currently stored in the `dataframe`. The CSV file will exclude any column
        headers.

        :return: None
        """
        self.dataframe.to_csv(self.prices_file, header=False)


