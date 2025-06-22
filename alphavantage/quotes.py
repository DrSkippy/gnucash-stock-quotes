#!/usr/bin/env -S poetry run python

import json
import logging
import pandas as pd
import requests
import time

from alphavantage.db_utils import QuoteDatabase


class TickerQuotes:
    HIGH_LOW_CLOSE_VOLUME_ = ["open", "high", "low", "close", "volume"]
    TAG_STOCKS_ = "2. Symbol"
    TAG_CRYPTO_ = "2. Digital Currency Code"
    KEY_STOCKS_ = "Time Series (Daily)"
    KEY_CRYPTO_ = "Time Series (Digital Currency Daily)"
    KEY_META_DATA_ = "Meta Data"
    ERROR_MESSAGE_ = "Error Message"
    RATE_DELAY = 0  # for free tier 11 sec delay between requests
    TICKERS_FILE = "./tickers.json"
    QUOTES_FILE = "./data/quotes.json"

    def __init__(self, filename=TICKERS_FILE, tickers=None):
        """
        Initializes an instance of the class, setting up configurations, tickers,
        and database schema as needed. Reads the configurations from a file and
        ensures the integrity of setup by comparing the keys for URLs. If a list
        of tickers is provided, it uses it; otherwise, it defaults to tickers from
        the configuration file. Sets up a database instance and creates the
        necessary schema.

        :param filename: Path to the JSON configuration file.
        :type filename: str
        :param tickers: Optional dictionary mapping tickers to data sources.
        :type tickers: dict, optional
        """
        with open(filename, "r") as fin:
            config = json.load(fin)
            logging.info(f"read from {filename}: {len(config)} records")
        self.key = config["configuration"]["key"]
        self.url_keys = config["configuration"]["url_base"].keys()
        url_keys_test = config["tickers"].keys()
        assert (self.url_keys == url_keys_test)
        self.url_base = config["configuration"]["url_base"]
        if tickers is None:
            self.tickers = config["tickers"]
        else:
            self.tickers = tickers
        self.db = QuoteDatabase(config)
        self.db.create_tables()

    def _process_record(self, t_dict):
        """
        {'Meta Data':
          {'1. Information': 'Daily Prices (open, high, low, close) and Volumes',
           '2. Symbol': 'NASDX',
           '3. Last Refreshed': '2024-09-19',
           '4. Output Size': 'Compact',
           '5. Time Zone': 'US/Eastern'},
           'Time Series (Daily)':
              {'2024-09-19':
                 {'1. open': '39.9000',
                 '2. high': '39.9000',
                 '3. low': '39.9000',
                 '4. close': '39.9000',
                 '5. volume': '0'},
              ...
        """
        if self.KEY_META_DATA_ not in t_dict:
            logging.error(f"Error: {t_dict.keys()}")
            return None, None

        if self.ERROR_MESSAGE_ in t_dict:
            logging.error(f"Error: {t_dict[self.ERROR_MESSAGE_]}")
            return None, None

        if self.TAG_STOCKS_ in t_dict[self.KEY_META_DATA_]:
            symbol = t_dict[self.KEY_META_DATA_][self.TAG_STOCKS_]
            logging.info(f"Processing {symbol} as stocks")
            df = pd.DataFrame().from_dict(t_dict[self.KEY_STOCKS_], orient="index")
        elif self.TAG_CRYPTO_ in t_dict[self.KEY_META_DATA_]:
            symbol = t_dict[self.KEY_META_DATA_][self.TAG_CRYPTO_]
            logging.info(f"Processing {symbol} as crypto")
            df = pd.DataFrame().from_dict(t_dict[self.KEY_CRYPTO_], orient="index")
        else:
            logging.error(f"Error: {t_dict[self.KEY_META_DATA_].keys()}")
            return None, None

        df.columns = self.HIGH_LOW_CLOSE_VOLUME_
        df.open = df.open.astype(float).fillna(0.0)
        df.high = df.high.astype(float).fillna(0.0)
        df.low = df.low.astype(float).fillna(0.0)
        df.close = df.close.astype(float).fillna(0.0)
        df.volume = df.volume.astype(float).fillna(0.0)
        df["symbol"] = symbol
        df["currency"] = "USD"
        df["namespace"] = "NASDAQ"
        logging.info(df.head())
        return df, symbol

    def print_tickers(self):
        """
        Prints a formatted list of tickers grouped by their market/source.

        Example output:
        Tickers:
        ├── stocks
        │   ├── AAPL
        │   ├── MSFT
        │   └── GOOGL
        └── crypto
            ├── BTC
            └── ETH
        """
        print("Tickers:")
        for idx, (market, tickers) in enumerate(self.tickers.items()):
            # Print market name with proper tree symbol
            is_last_market = idx == len(self.tickers) - 1
            market_prefix = "└──" if is_last_market else "├──"
            print(f"{market_prefix} {market}")

            # Print tickers for this market
            for i, ticker in enumerate(tickers):
                is_last_ticker = i == len(tickers) - 1
                ticker_prefix = "    └──" if is_last_ticker else "    ├──"
                if not is_last_market:
                    ticker_prefix = ticker_prefix.replace("    ", "│   ")
                print(f"{ticker_prefix} {ticker}")

    def fetch_quotes(self):
        """
        Fetches financial quotes for a set of tickers from specified URLs.

        This function iterates over a collection of URL keys and associated
        tickers to fetch financial data. For each ticker, it constructs the
        request URL using the provided base URL, ticker, and authentication key.
        It sends HTTP GET requests to retrieve JSON responses. The function also
        implements a delay between requests to adhere to the rate-limiting
        restrictions of the API.

        :raises requests.RequestException: If a network-related error occurs during
                                           the GET request.
        :raises json.JSONDecodeError: If the API's response cannot be parsed into
                                      JSON.
        :raises KeyError: If an expected key is missing in the JSON response.

        :return: A list of JSON responses retrieved for the provided tickers.
        :rtype: list[dict]
        """
        results = []
        for key in self.url_keys:
            for t in self.tickers[key]:
                logging.info('Getting ticker = {}'.format(t))
                url = self.url_base[key].format(t, self.key)
                logging.info('url = {}'.format(url))
                res = requests.get(url)
                logging.info('resp = {}'.format(res))
                res_json = res.json()
                results.append(res_json)
                logging.info(f"Waiting {self.RATE_DELAY} sec...")
                time.sleep(self.RATE_DELAY)
        return results

    def save_quotes(self, results, filename=QUOTES_FILE):
        """
        Save provided quotes data to a JSON file and database.

        This method processes the provided list of quotes and saves them in
        two different formats: a JSON file in the local file system and as records
        in a database. It creates data frames for database insertion and writes
        the data efficiently using predefined methods.

        :param results: A list of quotes, where each quote is represented as a dictionary.
        :param filename: An optional name of the JSON file where the quotes will be saved.
                         Defaults to the constant value QUOTES_FILE.
        :return: None
        """
        # Save to JSON file
        with open(filename, "w") as fout:
            logging.info("writing {} records...".format(len(results)))
            fout.write(json.dumps(results))

        # Save to database
        dfs = self.make_dataframes_list(results)
        for df in dfs:
            self.db.save_quotes(df)

    def read_quotes(self, filename=None, start_date=None, end_date=None, symbols=None):
        """
        Reads stock quotes data either from a JSON file or from a database, depending
        on the provided parameters. If a `filename` is specified, the data will be read
        from the file, otherwise it will fetch data from the database with the provided
        filter parameters.

        :param filename: Optional; Path to a JSON file containing the complete stock
                         quotes dataset.
        :type filename: str, optional
        :param start_date: Optional; Start date for the filtered data query when fetching
                           from the database.
        :type start_date: datetime.date, optional
        :param end_date: Optional; End date for the filtered data query when fetching
                         from the database.
        :type end_date: datetime.date, optional
        :param symbols: Optional; List of stock symbols to be filtered in the query
                        when fetching from the database.
        :type symbols: list of str, optional
        :return: List of Pandas DataFrames containing the stock quotes.
        :rtype: list of pandas.DataFrame
        """
        if filename:
            # Use JSON file for full dataset
            with open(filename, "r") as fin:
                results = json.load(fin)
            logging.info("read {} records...".format(len(results)))
            return self.make_dataframes_list(results)
        else:
            # Use database for filtered queries
            return self.db.read_quotes(start_date, end_date, symbols)

    def make_dataframes_list(self, results):
        """
        Parses and processes a list of query results to produce a list of filtered Pandas
        DataFrames. Each resulting DataFrame contains specific columns and is filtered
        for entries after '2016-01-01'.

        :param results: A list of dictionaries, where each dictionary represents query
            records to be processed.
        :type results: list
        :return: A list of Pandas DataFrames, where each DataFrame contains filtered and
            processed stock data including columns such as "namespace", "symbol", "close",
            and "currency".
        :rtype: list[pd.DataFrame]
        """
        df_list = []
        for q in results:
            df, symbol = self._process_record(q)
            if df is None:
                logging.error(
                    f"Error skipping processing record for {q.get(self.KEY_META_DATA_, {}).get(self.TAG_STOCKS_, 'Unknown')} due to error. See logs for details.")
                continue
            df = df.sort_index()
            df_list.append(df[["namespace", "symbol", "close", "currency"]][(df.index > '2016-01-01')])
        return df_list

    def make_wide_dataframe(self, dfs):
        """
        Transforms a long-format DataFrame into a wide-format DataFrame where each distinct
        symbol becomes a column and the rows represent corresponding 'close' values indexed
        by the 'date' column. It filters out columns where all entries are missing (NaN),
        and logs statistical information about the resulting DataFrame.

        :param dfs: Input pandas DataFrame in long format containing 'date', 'symbol',
            and 'close' columns.
        :type dfs: pandas.DataFrame
        :return: A wide-format DataFrame with 'date' as the index and symbols as columns
            containing 'close' values. Columns with all NaN values are removed.
        :rtype: pandas.DataFrame
        """
        df = dfs[["date", "symbol", "close"]].pivot_table(
            "close", index="date", columns="symbol"
        )
        df.dropna(axis=1, how="all", inplace=True)
        logging.info(f"DataFrame stats:\n{df.describe()}")
        return df

    def concatenate_dataframes(self, df_list) -> pd.DataFrame:
        """
        Concatenates a list of pandas DataFrame objects into a single DataFrame.

        This method takes a list of DataFrame objects and concatenates them along the
        default axis (axis=0). If the provided input is not a list, it directly
        returns the input. This ensures flexibility when dealing with a single DataFrame
        or a pre-concatenated input. It does not modify the original DataFrames.

        :param df_list: A list of pandas DataFrame objects to be concatenated, or a
            single non-list input if no concatenation is required.
        :type df_list: list[pd.DataFrame] | pd.DataFrame

        :return: A concatenated pandas DataFrame if given a list, or the
            original input if not a list.
        :rtype: pd.DataFrame
        """
        return pd.concat(df_list) if isinstance(df_list, list) else df_list

    def __del__(self):
        """
        Cleans up resources associated with the instance by closing the database connection
        if it exists. This method is a destructor called automatically when the object is
        garbage collected, ensuring proper resource deallocation.

        :return: None
        """
        if hasattr(self, 'db'):
            self.db.close()

