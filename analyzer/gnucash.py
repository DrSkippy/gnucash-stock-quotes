import pandas as pd
from analyzer.plots import plot_quotes


class Gnucash:
    PRICES_FILE = "./data/prices.csv"

    def __init__(self, dfs):
        plot_quotes(dfs)
        self.save_gnucash_quotes(dfs)

    def save_gnucash_quotes(self, dfs, filename=PRICES_FILE):
        if isinstance(dfs, list):
            df_out = pd.concat(dfs)
        else:
            df_out = dfs
        df_out.to_csv(filename, header=False)
