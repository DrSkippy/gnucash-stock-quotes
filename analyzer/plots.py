import logging

import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

PDF_FILE = "./data/quotes.pdf"


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

    def plot_quotes(self, dfs, ticker1, ticker2, filename="./correlations.pdf"):
        with PdfPages(filename) as pdf:
            logging.info("plotting {ticker1} vs {ticker2} dataframes")
            for df in dfs:
                symbol = df.symbol[-1].strip()
                if symbol == ticker1:
                    logging.info("  plotting symbol={} len={}".format(symbol, len(df.close)))
                    fig = df.plot(x="date", y="close", figsize=[10, 5], title="ticker={}".format(symbol)).get_figure()
                    pdf.savefig(fig)
                    ticker1_closes = df.close
                elif symbol == ticker2:
                    logging.info("  plotting symbol={} len={}".format(symbol, len(df.close)))
                    fig = df.plot(x="date", y="close", figsize=[10, 5], title="ticker={}".format(symbol)).get_figure()
                    pdf.savefig(fig)
                    ticker2_closes = df.close
            f = plt.figure(figsize=[10, 10])
            plt.plot(ticker1_closes, ticker2_closes, "*-")
            plt.xlabel(ticker1)
            plt.ylabel(ticker2)
            pdf.savefig(f)
            plt.close()
