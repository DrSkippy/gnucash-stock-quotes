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

The keys in the tickers dictionary are Gnucash "namespaces".

```{
	"configuration" : 
	{
		"key" : "<YOUR KEY>",
		"url_base" : "https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol={}&apikey={}"
	},
	"tickers": {
		"AMEX": [
			"FBRSX",
			"TRPDX",
...
		"NASDAQ": [
			"AKAM",
			"FMCSX",
...
		]
	}
}
```
