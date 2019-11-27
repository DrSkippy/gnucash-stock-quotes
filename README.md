# gnucash-stock-quotes


### Setup

```
poetry install
```

### Running

```
poetry run python bin/fetch.py 
```
Or to process quotes already fetched from  Alphavantage:
```
poetry run python bin/from_disk.py
```
### tickers.json

```{
	"configuration" : 
	{
		"key" : "<YOUR KEY>",
		"url_base" : "https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol={}&apikey={}"
	},
	"tickers" :
	["AKAM",
	"FBRSX",
	"FDVLX",
    ...
	"VFINX",
	"VMMXX",
	"VTTVX"]
}
```
