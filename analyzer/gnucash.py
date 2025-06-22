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
        """Process and save the quotes data."""
        plot_stock_prices(self.dataframe)
        self.save_gnucash_quotes()

    def save_gnucash_quotes(self) -> None:
        """Save processed quotes to CSV file."""
        self.dataframe.to_csv(self.prices_file, header=False)


