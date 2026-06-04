# gnucash-stock-quotes

**Safe Haven Adventure Kit (SHaK)** — fetches daily stock and crypto quotes from Alpha Vantage, persists them to a PostgreSQL database, calculates custom market indexes, and generates reports for GnuCash import.

---

## Setup

```bash
poetry install
```

Copy `tickers.json.example` to `tickers.json` and fill in your Alpha Vantage API key and PostgreSQL credentials (see [Configuration](#configuration) below).

---

## Running

### Fetch today's quotes and save to the database

```bash
./bin/daily_fetch.py
# or via the poetry runner:
./runner.sh
```

Tables are created automatically on first run.

### Analyse data and generate reports

```bash
./bin/shak.py -h
```

```
usage: shak.py [-h] [-c SECURITY [SECURITY ...]] [-l] [-i INDEX_NAME]
               [-s START_DATE] [-f FILE] [-p COMP_PORTFOLIO [COMP_PORTFOLIO ...]]
               {compare,gnucash,index,seed-indexes}

positional arguments:
  {compare,gnucash,index,seed-indexes}
                        compare       — correlation plot for two securities
                        gnucash       — generate a GnuCash quotes CSV
                        index         — analyse and plot market indexes
                        seed-indexes  — load index definitions from JSON into the database

options:
  -c, --compare-securities   2 security symbols
  -l, --list                 List available securities in the database
  -i, --index-name           Index to analyse (e.g. "equal_weight_price_index_app_delivery")
  -s, --start-date           Start date in YYYY-MM-DD format
  -f, --file                 Path to index definitions JSON (default: ./indexes.json)
  -p, --compare-portfolio    Comparison portfolio, e.g. "FFIV 0" for default allocation
```

**Examples:**

```bash
# Compare two securities
./bin/shak.py compare -c FFIV NET

# Generate GnuCash import file
./bin/shak.py gnucash

# Analyse an index and plot against a benchmark
./bin/shak.py index -i equal_weight_price_index_app_delivery -p FFIV 0

# Seed index definitions from indexes.json into the database
./bin/shak.py seed-indexes

# Seed from a different file
./bin/shak.py seed-indexes -f /path/to/other_indexes.json
```

---

## Database

**PostgreSQL** — tables are created automatically by `QuoteDatabase.create_tables()`.

| Table | Description |
|---|---|
| `quotes` | Daily close prices; range-partitioned by year (`quotes_2016` … `quotes_future`) |
| `asset_indexes` | Index definitions (name, type, created_date, portfolio_value) |
| `index_members` | Member symbols per index with optional market-cap weight |
| `index_weights` | Computed share counts per symbol per index |
| `index_history` | Computed time-series index values; range-partitioned by year |

The `quotes` and `index_history` tables use **declarative range partitioning by date** for efficient time-range queries and maintenance.

### Seeding index definitions

On first use with an empty database, `AssetIndex` falls back to `indexes.json`.  
To persist definitions so they load from the DB on future runs — or to push edits to `indexes.json` into the DB — use the `seed-indexes` command:

```bash
./bin/shak.py seed-indexes
```

This is an upsert, so it's safe to run again after adding or editing entries in `indexes.json`.

---

## Configuration

### `tickers.json`

```json
{
  "configuration": {
    "key": "<your_alphavantage_api_key>",
    "url_base": {
      "DIGITAL_CURRENCY_DAILY": "https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={}&market=USD&apikey={}",
      "TIME_SERIES_DAILY": "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={}&apikey={}"
    },
    "database": {
      "host": "<db_host>",
      "port": 5434,
      "user": "<db_user>",
      "password": "<db_password>",
      "database": "stock_quotes"
    }
  },
  "tickers": {
    "DIGITAL_CURRENCY_DAILY": ["ETH", "GTC"],
    "TIME_SERIES_DAILY": ["SPY", "VOO", "FFIV", "NET", "CRWD", "..."]
  }
}
```

### `indexes.json`

Defines custom market indexes. Three weighting strategies are supported:

| Type | Description |
|---|---|
| `EQUAL_WEIGHT` | Equal dollar allocation to each member at inception |
| `CONSTANT` | Equal share count per member (price-weighted) |
| `MARKET_CAP` | Allocation proportional to market capitalisation at inception |

```json
{
  "asset_indexes": [
    {
      "NAME": "equal_weight_price_index_app_delivery",
      "TYPE": "EQUAL_WEIGHT",
      "CREATED_DATE": "2025-01-22",
      "MEMBERS": ["FFIV", "NET", "SNOW", "FTNT", "ATEN", "AKAM", "CRWD"]
    },
    {
      "NAME": "market_cap_index_app_delivery",
      "TYPE": "MARKET_CAP",
      "CREATED_DATE": "2025-01-22",
      "MEMBERS": ["FFIV", "NET", "SNOW", "FTNT", "ATEN", "AKAM", "CRWD"],
      "MARKET_CAP": [12.802, 28.5, 37.75, 58.6, 1.01, 15.098, 70.22]
    }
  ]
}
```

---

## Dashboard

An interactive Plotly Dash web app for browsing indexes, comparing stocks, and exploring correlations.

### Pages

| Page | URL | Description |
|---|---|---|
| Index Browser | `/` | Index history chart, member weights table, Recalculate action |
| Compare | `/compare` | Index vs stock rebased to 100, rolling correlation subplot |
| Correlations | `/correlations` | Two-symbol price series and scatter/correlation plot |
| Stocks | `/stocks` | Multi-symbol normalized price chart, Fetch Latest Quotes action |

### Build and push

```bash
docker build -t localhost:5000/slak-dashboard:latest -f ./Dockerfile.dashboard .
docker push localhost:5000/slak-dashboard:latest
```

### Deploy (Dockge)

Paste the contents of `docker-compose.yml` into a new Dockge stack and set the environment variables:

| Variable | Required | Description |
|---|---|---|
| `DB_HOST` | yes | PostgreSQL host |
| `DB_PORT` | yes | PostgreSQL port |
| `DB_USER` | yes | PostgreSQL user |
| `DB_PASSWORD` | yes | PostgreSQL password |
| `DB_NAME` | yes | Database name |
| `AV_API_KEY` | fetch action only | Alpha Vantage API key |
| `TICKERS_STOCKS` | fetch action only | Comma-separated stock symbols |
| `TICKERS_CRYPTO` | fetch action only | Comma-separated crypto symbols |

No volume mounts are required — all config is passed via environment variables.

### PostgreSQL access for Docker containers

Docker containers run in the `172.x.x.x` subnet. PostgreSQL's `pg_hba.conf` must allow connections from that range. Add this line (before the `local` catch-all) and reload:

```
# pg_hba.conf
host    slak-dashboard    all    172.0.0.0/8    scram-sha-256
```

```bash
sudo systemctl reload postgresql
```

---

## Project layout

```
gnucash-stock-quotes/
├── alphavantage/
│   ├── db_utils.py         # QuoteDatabase: all PostgreSQL logic (quotes + indexes)
│   └── quotes.py           # TickerQuotes: Alpha Vantage API client
├── market_indexes/
│   ├── asset_index.py      # AssetIndex: portfolio weighting + time-series calculation
│   └── portfolio.py        # PortfolioAnalyzer: orchestrates AssetIndex for CLI
├── analyzer/
│   └── plots.py            # CorrelationsPlotter, plot_stock_prices
├── bin/
│   ├── daily_fetch.py      # Cron entry point
│   └── shak.py             # CLI
├── tests/                  # pytest unit tests (116 tests, no DB or network required)
├── indexes.json            # Index definitions (DB bootstrap / fallback)
├── tickers.json            # Runtime config — gitignored
├── pyproject.toml          # Poetry project
└── runner.sh               # Shell wrapper
```

---

## Tests

```bash
poetry run pytest tests/ -v
```

All tests are unit tests — they mock the database and filesystem, so no PostgreSQL connection or network access is required.

```
tests/test_db_utils.py    — QuoteDatabase (connection, DDL, quotes, index tables)
tests/test_quotes.py      — TickerQuotes (API response parsing, DataFrame shaping)
tests/test_asset_index.py — AssetIndex (portfolio math, DB integration hooks)
tests/test_plots.py       — CorrelationsPlotter, plot_stock_prices
```
