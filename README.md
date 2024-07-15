# gnucash-stock-quotes


### Setup

```
poetry install
```

### Run

```
poetry run python bin/fetch.py 
```
Or, to process quotes already fetched from  Alphavantage:
```
poetry run python bin/from_disk.py
```
### tickers.json

The keys in the tickers dictionary determine the Alphavantage end point and the
Gnucash "namespaces" are all set to "NASDAQ" (this means the Gnucash securities have
to be set to this namespace as well for imports to work properly).

```{
	"configuration" : 
	{
		"key" : "<YOUR KEY>",
		    "url_base": {
			"DIGITAL_CURRENCY_WEEKLY": "https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_WEEKLY&symbol={}&market=USD&apikey={}",
      			"TIME_SERIES_WEEKLY": "https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol={}&apikey={}"
			}
	},
	"tickers": {
    "DIGITAL_CURRENCY_WEEKLY": [
      "BTC",
      ... 
    ],
    "TIME_SERIES_WEEKLY": [
      "TWTR",
      ...
	]
	}
}
```
