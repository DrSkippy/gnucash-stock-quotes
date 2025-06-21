import logging
from typing import List, Optional, Union
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# Constants
QUOTES_PDF_PATH = "./data/quotes.pdf"
CORRELATIONS_PDF_PATH = "./data/correlations.pdf"
PLOT_FIGSIZE_SINGLE = [12, 5]
PLOT_FIGSIZE_CORRELATION = [10, 10]
ANNOTATION_INTERVAL = 7
ANNOTATION_FONTSIZE = 6
DATE_FORMAT_LENGTH = 10


def plot_stock_prices(dataframes: pd.DataFrame,
                      filename: str = QUOTES_PDF_PATH,
                      symbols: Optional[List[str]] = None) -> None:
    """Plot stock prices for multiple symbols and save to PDF."""
    if symbols is None:
        symbols = list(dataframes.symbol.unique())

    with PdfPages(filename) as pdf:
        logging.info(f"Plotting {len(dataframes)} dataframes")
        for symbol in symbols:
            df = dataframes[dataframes.symbol == symbol]
            logging.info(f"Plotting symbol={symbol} len={len(df.close)}")
            fig = df.plot(
                x="date",
                y="close",
                figsize=PLOT_FIGSIZE_SINGLE,
                title=f"ticker={symbol}"
            ).get_figure()
            pdf.savefig(fig)
        plt.close()


class CorrelationsPlotter:
    def __init__(self, dataframes: pd.DataFrame):
        self.dataframes = dataframes.reset_index(drop=True)
        print(self.dataframes.info())

    def plot_correlation(self,
                         ticker1: str,
                         ticker2: str,
                         filename: str = CORRELATIONS_PDF_PATH) -> None:
        """Plot correlation analysis between two tickers."""
        with PdfPages(filename) as pdf:
            logging.info(f"Plotting {ticker1} vs {ticker2} dataframes")

            # Plot individual stock prices
            df1 = self._get_ticker_data(ticker1)
            df2 = self._get_ticker_data(ticker2)
            self._plot_single_ticker(df1, ticker1, pdf)
            self._plot_single_ticker(df2, ticker2, pdf)

            # Plot correlation
            merged_df = self._prepare_correlation_data(df1, df2, ticker1, ticker2)
            self._plot_correlation_scatter(merged_df, ticker1, ticker2, pdf)

            plt.close()

    def _get_ticker_data(self, ticker: str) -> pd.DataFrame:
        return self.dataframes[self.dataframes.symbol == ticker]

    def _plot_single_ticker(self, df: pd.DataFrame, ticker: str, pdf: PdfPages) -> None:
        logging.info(f"Plotting symbol={ticker} len={len(df.close)}")
        fig = df.plot(
            x="date",
            y="close",
            figsize=PLOT_FIGSIZE_SINGLE,
            title=f"ticker={ticker}"
        ).get_figure()
        pdf.savefig(fig)

    def _prepare_correlation_data(self,
                                  df1: pd.DataFrame,
                                  df2: pd.DataFrame,
                                  ticker1: str,
                                  ticker2: str) -> pd.DataFrame:
        merged_df = pd.merge_asof(
            df1, df2,
            on="date",
            suffixes=(f"_{ticker1}", f"_{ticker2}")
        )[["date", f"close_{ticker1}", f"close_{ticker2}"]]
        merged_df.set_index("date", inplace=True)
        print(merged_df.corr())
        return merged_df

    def _plot_correlation_scatter(self,
                                  df: pd.DataFrame,
                                  ticker1: str,
                                  ticker2: str,
                                  pdf: PdfPages) -> None:
        ax = df.plot(
            x=f"close_{ticker1}",
            y=f"close_{ticker2}",
            style="*-",
            figsize=PLOT_FIGSIZE_CORRELATION
        )

        for i, (idx, row) in enumerate(df.iterrows()):
            if i % ANNOTATION_INTERVAL == 0:
                ax.annotate(
                    str(idx)[:DATE_FORMAT_LENGTH],
                    (row[f"close_{ticker1}"], row[f"close_{ticker2}"]),
                    textcoords="offset points",
                    xytext=(0, 5),
                    ha='center',
                    fontsize=ANNOTATION_FONTSIZE
                )

        plt.xlabel(ticker1)
        plt.ylabel(ticker2)
        pdf.savefig(ax.get_figure())
