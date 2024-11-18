import logging

import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

class Compare:

    def __init__(self, dfs):
        self.dfs = dfs

    def plot_quotes(self, dfs, ticker1, ticker2, filename="./correlations.pdf"):
        with PdfPages(filename) as pdf:
            logging.info("plotting {ticker1} vs {ticker2} dataframes")
            for df in dfs:
                symbol = df.symbol[-1].strip()
                if symbol == ticker1:
                    logging.info("  plotting symbol={} len={}".format(symbol, len(df.close)))
                    fig = df.plot(y="close", figsize=[12, 5], title="ticker={}".format(symbol)).get_figure()
                    pdf.savefig(fig)
                    ticker1_closes = df.close
                elif symbol == ticker2:
                    logging.info("  plotting symbol={} len={}".format(symbol, len(df.close)))
                    fig = df.plot(y="close", figsize=[12, 5], title="ticker={}".format(symbol)).get_figure()
                    pdf.savefig(fig)
                    ticker2_closes = df.close
            f = plt.figure()
            f.figsize=[12, 12]
            plt.plot(ticker1_closes, ticker2_closes, "*-")
            plt.xlabel(ticker1)
            plt.ylabel(ticker2)
            pdf.savefig(f)
            plt.close()