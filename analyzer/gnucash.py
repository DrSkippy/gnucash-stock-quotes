import logging

import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


class Gnucash:

    PRICES_FILE = "./data/prices.csv"
    PDF_FILE = "./data/quotes.pdf"

    def __init__(self, dfs):
        self.plot_quotes(dfs)
        self.save_gnucash_quotes(dfs)

    def plot_quotes(self, dfs, filename=PDF_FILE):
        with PdfPages(filename) as pdf:
            logging.info("plotting {} dataframes".format(len(dfs)))
            for symbol in dfs.symbol.unique():
                df = dfs[dfs.symbol == symbol]
                logging.info("  plotting symbol={} len={}".format(symbol, len(df.close)))
                fig = df.plot(y="close", figsize=[12, 5], title="ticker={}".format(symbol)).get_figure()
                pdf.savefig(fig)
            plt.close()

    def save_gnucash_quotes(self, dfs, filename=PRICES_FILE):
        if isinstance(dfs, list):
            df_out = pd.concat(dfs)
        else:
            df_out = dfs
        df_out.to_csv(filename, header=False)
