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
        self.dataframes = dataframes

    def process_quotes(self) -> None:
        """Process and save the quotes data."""
        plot_stock_prices(self.dataframes)
        self.save_gnucash_quotes()

    def save_gnucash_quotes(self) -> None:
        """Save processed quotes to CSV file."""
        df_out = self._concatenate_dataframes()
        df_out.to_csv(self.prices_file, header=False)

    def _concatenate_dataframes(self) -> pd.DataFrame:
        """Combine multiple dataframes if needed."""
        return pd.concat(self.dataframes) if isinstance(self.dataframes, list) else self.dataframes
