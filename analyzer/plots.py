import logging

import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

PDF_FILE = "./data/quotes.pdf"
PDF_CORRELATIONS_FILE = "./data/correlations.pdf"


def plot_quotes(dfs, filename=PDF_FILE, symbol_list=None):
    if symbol_list is None:
        symbol_list: List[Any] = list(dfs.symbol.unique())
    with PdfPages(filename) as pdf:
        logging.info("plotting {} dataframes".format(len(dfs)))
        for symbol in symbol_list:
            df = dfs[dfs.symbol == symbol]
            logging.info("  plotting symbol={} len={}".format(symbol, len(df.close)))
            fig = df.plot(x="date", y="close", figsize=[12, 5], title="ticker={}".format(symbol)).get_figure()
            pdf.savefig(fig)
        plt.close()


class CorrelationsPlotter:

    def __init__(self, dfs):
        self.dfs = dfs

    def plot_quotes(self, dfs, ticker1, ticker2, filename=PDF_CORRELATIONS_FILE):
        with (PdfPages(filename) as pdf):
            logging.info("plotting {ticker1} vs {ticker2} dataframes")
            df1 = dfs[dfs.symbol == ticker1]
            df2 = dfs[dfs.symbol == ticker2]

            logging.info("  plotting symbol={} len={}".format(ticker1, len(df1.close)))
            fig = df1.plot(x="date", y="close", figsize=[10, 5], title="ticker={}".format(ticker1)).get_figure()
            pdf.savefig(fig)
            ticker1_closes = df1.close
            logging.info("  plotting symbol={} len={}".format(ticker2, len(df2.close)))
            fig = df2.plot(x="date", y="close", figsize=[10, 5], title="ticker={}".format(ticker2)).get_figure()
            pdf.savefig(fig)
            ticker2_closes = df2.close

            merged_df = pd.merge_asof(df1, df2, on="date", suffixes=("_" + ticker1, "_" + ticker2))[["date", "close_" + ticker1, "close_" + ticker2]]
            merged_df.set_index("date", inplace=True)
            print(merged_df.corr())

            ax = merged_df.plot(x="close_" + ticker1, y="close_" + ticker2, style="*-", figsize=[10, 10])
            fig = ax.get_figure()
            counter = 0
            for i, row in merged_df.iterrows():
                if counter % 7 == 0:
                    ax.annotate(str(i)[:10], (row["close_" + ticker1], row['close_' + ticker2]),
                            textcoords="offset points", xytext=(0, 5), ha='center', fontsize=6)
                counter += 1
            plt.xlabel(ticker1)
            plt.ylabel(ticker2)
            pdf.savefig(fig)
            plt.close()
