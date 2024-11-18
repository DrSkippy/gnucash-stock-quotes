import csv

import pandas as pd


class CoinbaseTransactionReport:

    def __init__(self,
                 filename="/home/scott/Downloads/csv_version.csv"):
        """
        https://accounts.coinbase.com/statements to download the csv
        :param filename:
        """
        with open(filename, "r") as infile:
            preamble = True
            data = []
            rdr = csv.reader(infile)
            for row in rdr:
                if len(row) > 0 and row[0] == 'ID':
                    preamble = False
                    self.header = row
                elif not preamble:
                    data.append(row)
            self.df = pd.DataFrame(data, columns=self.header)
            self.df = self.df.replace(r'^\s*$', 0.0, regex=True)
            self.df["Quantity Transacted"] = self.df["Quantity Transacted"].apply(float)
            self.df["Price at Transaction"] = self.df["Price at Transaction"].str.replace('$', '').astype(float)
            self.df["Subtotal"] = self.df["Subtotal"].str.replace('$', '').astype(float)
            self.df["Fees and/or Spread"] = self.df["Fees and/or Spread"].str.replace('$', '').astype(float)
            self.df["Total (inclusive of fees and/or spread)"] = self.df["Total (inclusive of fees and/or spread)"].str.replace('$', '').astype(float)
            self.df["Average Price"] = self.df["Total (inclusive of fees and/or spread)"] / self.df["Quantity Transacted"]

    def subtotals(self):
        self.current_prices()
        _df = self.df.groupby(["Asset", "Transaction Type"])[[
            'Quantity Transacted', "Total (inclusive of fees and/or spread)", "Fees and/or Spread", "Average Price"]].sum()
        _df.reset_index(inplace=True)
        _df = pd.merge(_df, self.prices, on="Asset")
        _df["current_value"] = _df["Quantity Transacted"] * _df["price"]
        _df["gain"] = (_df["current_value"] - _df["Total (inclusive of fees and/or spread)"]) / _df["Total (inclusive of fees and/or spread)"]
        return _df

    def current_prices(self, filename="/home/scott/Working/gnucash-stock-quotes/data/prices.csv"):
        column_names=["price date", "exchange", "Asset", "price", "currency"]
        _prices = pd.read_csv(filename, names=column_names, parse_dates=["price date"])
        self.prices = pd.DataFrame(columns=column_names)
        for asset in enumerate(_prices["Asset"].unique()):
            try:
                _x = _prices.loc[_prices["Asset"] == asset[1]]
                self.prices = self.prices.append(_prices.iloc[[_x["price date"].idxmax()]], ignore_index=True)
            except KeyError:
                print(f"{asset}Missing")


if __name__ == "__main__":
    a = CoinbaseTransactionReport()
    print(a.df)
    print(a.subtotals())
    print(a.prices)
