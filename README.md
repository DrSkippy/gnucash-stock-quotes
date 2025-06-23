# gnucash-stock-quotes

### Setup

```
poetry install
```
### Set up configuraiton files




### Run the fetch script to download stock quotes and save to database

```
./bin/daily_fetch.py
```

### Run the script to analyse data and generate reports

```
$ ./bin/shak.py -h
usage: shak.py [-h] [-c SECURITY [SECURITY ...]] [-l] [-i INDEX_NAME] [-s START_DATE] [-p COMP_PORTFOLIO [COMP_PORTFOLIO ...]]
               {compare,gnucash,index}

**Save Haven Adventure Kit** (SHaK) is a tool for analyzing and plotting stock market data. It allows you to compare two securities,
create a gnucash quotes file, or analyze market indexes.

positional arguments:
  {compare,gnucash,index}
                        Command to execute: 'compare' for comparing securities, 'gnucash' for creating a gnucash quotes file, or 'index'
                        for analyzing market indexes.

options:
  -h, --help            show this help message and exit
  -c SECURITY [SECURITY ...], --compare-securities SECURITY [SECURITY ...]
                        2 security symbols
  -l, --list            List available securities in the database
  -i INDEX_NAME, --index-name INDEX_NAME
                        Name of the index to analyze (e.g., "equal_weight", "constant", "market_cap")
  -s START_DATE, --start-date START_DATE
                        Start date for the analysis in YYYY-MM-DD format
  -p COMP_PORTFOLIO [COMP_PORTFOLIO ...], --compare-portfolio COMP_PORTFOLIO [COMP_PORTFOLIO ...]
                        Portfolio to compare against the index, e.g., "FFIV 0" for default allocation to FFIV
```

### E.g. Run the script to generate a Gnucash quotes file

```
./bin/stak.py gnucash
```

Creates a CSV file for import into Gnucash.

### tickers.json

The keys in the tickers dictionary determine the Alphavantage end point and the
Gnucash "namespaces" are all set to "NASDAQ" (this means the Gnucash securities have
to be set to this namespace as well for imports to work properly).

```
{
  "configuration": {
    "key": "<your_alphavantage_api_key>",
    "url_base": {
      "DIGITAL_CURRENCY_DAILY": "https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={}&market=USD&apikey={}",
      "TIME_SERIES_DAILY": "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={}&apikey={}"
    },
    "database": {
      "host": "192.168.127.166",
      "port": 3306,
      "user": "<your_database_user>",
      "password": "<your_database_password>",
      "database": "stock_quotes"
    }
  },
  "tickers": {
    "DIGITAL_CURRENCY_DAILY": [
      "GTC",
      "ETH"
    ],
    "TIME_SERIES_DAILY": [
      "QBTS",
      "IONQ",
      ...
```

### indexes.json

```
{
  "asset_indexes": [
    {
      "NAME": "equal_weight_price_index_app_delivery",
      "TYPE": "EQUAL_WEIGHT",
      "CREATED_DATE": "2025-01-22",
      "MEMBERS": [
        "FFIV",
        "NET",
        "SNOW",
        "FTNT",
        "ATEN",
        "AKAM",
        "CRWD"
      ]
    },
    {
      "NAME": "constant_index_app_delivery",
      "CREATED_DATE": "2025-01-22",
      "TYPE": "CONSTANT",
      "MEMBERS": [
        "FFIV",
        "NET",
        "SNOW",
        "FTNT",
        "ATEN",
        "AKAM",
        "CRWD"
      ]
    },
    {
      "NAME": "market_cap_index_app_delivery",
      "CREATED_DATE": "2025-01-22",
      "TYPE": "MARKET_CAP",
      "MEMBERS": [
        "FFIV",
        "NET",
        "SNOW",
        "FTNT",
        "ATEN",
        "AKAM",
        "CRWD"
      ],
      "MARKET_CAP": [
        12.802,
        28.5,
        37.75,
        58.6,
        1.01,
        15.098,
        70.22
      ]
    },
...
```

