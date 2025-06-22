import logging
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from typing import List, Optional, Union

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
    """
    Plots stock prices for the provided dataframes and writes the result to a PDF file.

    The function generates plots for stock data filtered by symbols and saves the
    plots into a PDF file. Each symbol's data is plotted separately and appended
    to the PDF. If no symbols are specified, plots will be generated for all unique
    symbols in the dataframes.

    :param dataframes: The input pandas DataFrame containing stock prices.
        It is expected to have at least the following columns: "symbol", and
        relevant data for plotting.
    :type dataframes: pd.DataFrame
    :param filename: The output filename for the PDF file where plots will
        be saved. Default value is a predefined path (QUOTES_PDF_PATH).
    :type filename: str
    :param symbols: An optional list of stock symbols to filter and plot.
        If not specified, plots will be generated for all unique symbols
        in the 'symbol' column of the input DataFrame.
    :type symbols: Optional[List[str]]
    :return: This function does not return any value.
    :rtype: None
    """
    if symbols is None:
        symbols = list(dataframes.symbol.unique())

    with PdfPages(filename) as pdf:
        logging.info(f"Plotting {len(dataframes)} dataframes")
        for symbol in symbols:
            df = dataframes[dataframes.symbol == symbol]
            CorrelationsPlotter._plot_single_ticker(df, symbol, pdf)
        plt.close()


class CorrelationsPlotter:
    """
    Facilitates the creation of correlation plots between stock tickers using
    provided price data.

    This class is built to analyze and visualize the correlations between
    different stock tickers by utilizing their historical price data. It supports
    data in both deep and wide formats and generates correlation plots in a
    specified PDF file. The plots include individual stock price trends as well
    as their scatter plot correlations.

    :ivar dataframes: DataFrames containing historical stock prices. Must have
        columns `symbol`, `date`, and `close` for deep format or individual symbol
        data in wide format.
    :type dataframes: pd.DataFrame
    """
    def __init__(self, dataframes: pd.DataFrame):
        """
        This class initializes an instance with a given pandas DataFrame, automatically resetting the index
        while dropping the old index and printing an overview of the DataFrame structure.

        Attributes:
            dataframes (pd.DataFrame): The DataFrame provided during object initialization, with its index reset.

        :param dataframes: The pandas DataFrame to initialize the class instance with. The index of this
            DataFrame will be reset.
        :type dataframes: pd.DataFrame
        """
        self.dataframes = dataframes.reset_index(drop=True)
        print(self.dataframes.info())

    def plot_correlation(self,
                         ticker1: str,
                         ticker2: str,
                         filename: str = CORRELATIONS_PDF_PATH) -> None:
        """
        Plots the correlation between two stock tickers using their respective time-series data
        and generates a PDF report with the resulting plots. This function supports both wide
        and deep dataframe formats. The PDF includes individual stock price plots for each ticker
        and a scatter plot illustrating the correlation between the two.

        :param ticker1: Symbol of the first stock ticker to analyze.
        :type ticker1: str
        :param ticker2: Symbol of the second stock ticker to analyze.
        :type ticker2: str
        :param filename: Filename or path for saving the generated PDF report. Defaults to the
            constant `CORRELATIONS_PDF_PATH`.
        :type filename: str, optional
        :return: None
        """
        df_type = "deep" # vs wide
        if ticker1 not in self.dataframes.symbol.unique():
            if ticker1 not in self.dataframes.columns:
                raise ValueError(f"Ticker {ticker1} not found in dataframes.")
            else:
                df_type = "wide"
        else:
            df_type = "deep"
        if ticker2 not in self.dataframes.symbol.unique():
            if ticker2 not in self.dataframes.columns:
                raise ValueError(f"Ticker {ticker2} not found in dataframes.")
            else:
                df_type = "wide"

        with PdfPages(filename) as pdf:
            logging.info(f"Plotting {ticker1} vs {ticker2} dataframes")
            if df_type == "deep":
                # Plot individual stock prices
                df1 = self._get_ticker_data(ticker1)
                df2 = self._get_ticker_data(ticker2)
                self._plot_single_ticker(df1, ticker1, pdf)
                self._plot_single_ticker(df2, ticker2, pdf)
            else: # "wide"
                # Plot wide format dataframes
                df1 = self.dataframes[[ticker1, "date"]].rename(columns={ticker1: "close"})
                df2 = self.dataframes[[ticker2, "date"]].rename(columns={ticker2: "close"})
                df1["symbol"] = ticker1
                df2["symbol"] = ticker2
                df1.set_index("date", inplace=True)
                df2.set_index("date", inplace=True)
                self._plot_single_ticker(df1, ticker1, pdf)
                self._plot_single_ticker(df2, ticker2, pdf)
            # Plot correlation
            merged_df = self._prepare_correlation_data(df1, df2, ticker1, ticker2)
            self._plot_correlation_scatter(merged_df, ticker1, ticker2, pdf)

            plt.close()

    def _get_ticker_data(self, ticker: str) -> pd.DataFrame:
        """
        Fetches the data for a specific stock ticker from the preloaded
        dataframes.

        :param ticker: Stock ticker symbol to fetch data for
        :type ticker: str
        :return: A DataFrame containing the stock data filtered by the provided ticker
        :rtype: pd.DataFrame
        """
        return self.dataframes[self.dataframes.symbol == ticker]

    @classmethod
    def _plot_single_ticker(self, df: pd.DataFrame, ticker: str, pdf: PdfPages) -> None:
        """
        Plots the data for a single ticker and writes the plot to a PDF file.

        This function is responsible for generating a plot for a specific ticker's
        data from the provided DataFrame and saving the resulting figure into
        the specified PdfPages object. The plot contains 'date' on the x-axis and
        'close' on the y-axis. A log message with details of the operation is also
        generated for tracking purposes.

        :param df: The DataFrame containing the ticker data, which includes
            'date' and 'close' columns.
        :type df: pd.DataFrame
        :param ticker: The ticker symbol for which the plot is generated.
        :type ticker: str
        :param pdf: A PdfPages object that stores the generated plot as a page
            in the managed PDF.
        :type pdf: PdfPages
        :return: This method does not return anything. It saves the plot directly
            to the provided PdfPages object.
        :rtype: None
        """
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
        """
        Prepares and returns a merged DataFrame containing data for correlation analysis
        between two input DataFrames, alongside the correlation matrix. The function
        utilizes asof merging to align the data by date, and ensures only the relevant
        columns with closing prices are retained. The resulting DataFrame is indexed
        by date and contains closing price data suffixed by the respective tickers.

        :param df1: DataFrame containing the first dataset with closing prices.
        :type df1: pd.DataFrame
        :param df2: DataFrame containing the second dataset with closing prices.
        :type df2: pd.DataFrame
        :param ticker1: Ticker symbol representing the first dataset.
        :type ticker1: str
        :param ticker2: Ticker symbol representing the second dataset.
        :type ticker2: str
        :return: DataFrame containing merged data with closing prices aligned by date
                 and indexed by date for correlation analysis.
        :rtype: pd.DataFrame
        """
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
        """
        Plots a correlation scatter plot of two ticker symbols based on their closing prices
        from the provided DataFrame. Data points are annotated at regular intervals, and the
        resulting plot is saved into the provided PdfPages object.

        :param df: DataFrame containing the data for both ticker symbols with columns
            named as 'close_<ticker1>' and 'close_<ticker2>' where ticker1 and ticker2
            are the symbols of the tickers being plotted.
        :type df: pd.DataFrame
        :param ticker1: The first ticker symbol to include on the x-axis of the scatter plot.
        :type ticker1: str
        :param ticker2: The second ticker symbol to include on the y-axis of the scatter plot.
        :type ticker2: str
        :param pdf: PdfPages object where the scatter plot figure will be saved.
        :type pdf: PdfPages
        :return: This function does not return any value.
        :rtype: None
        """
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
