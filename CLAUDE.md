# CLAUDE.md — gnucash-stock-quotes

## Project Layout

```
gnucash-stock-quotes/
├── alphavantage/           # Alpha Vantage API client + DB utilities
│   ├── db_utils.py         # QuoteDatabase: quotes + index tables (PostgreSQL)
│   └── quotes.py           # TickerQuotes: fetch/save/read quote data
├── market_indexes/         # Index calculation engine
│   ├── asset_index.py      # AssetIndex: portfolio weighting + time-series calc
│   └── portfolio.py        # PortfolioAnalyzer: wrapper for CLI usage
├── bin/
│   ├── daily_fetch.py      # Cron entry point: fetch quotes and save to DB
│   └── shak.py             # CLI: analysis, index plots, GnuCash export
├── data/                   # Output files (PDFs, CSVs, JSON cache)
├── indexes.json            # Index definitions (bootstrap / fallback)
├── tickers.json            # API key, DB config, ticker lists (gitignored in practice)
├── pyproject.toml          # Poetry project
└── runner.sh               # Shell wrapper (sets PYTHONPATH, invokes Poetry)
```

## Running

**All Python commands use Poetry:**
```bash
poetry run python bin/daily_fetch.py      # fetch & persist today's quotes
poetry run python bin/shak.py index       # run index analysis
poetry run python bin/shak.py --help      # full CLI options
```

## Key Files

- `alphavantage/db_utils.py` — `QuoteDatabase` class; all DB logic (quotes, index definitions, weights, history)
- `alphavantage/quotes.py` — `TickerQuotes`; wraps Alpha Vantage API + QuoteDatabase
- `market_indexes/asset_index.py` — `AssetIndex`; portfolio weighting, index time-series calculation
- `market_indexes/portfolio.py` — `PortfolioAnalyzer`; orchestrates AssetIndex for CLI
- `indexes.json` — index definitions (used as fallback when DB has no definitions)
- `tickers.json` — runtime config (API key, DB connection, ticker symbols)

## Configuration (`tickers.json`)

```json
{
  "configuration": {
    "key": "<alpha_vantage_api_key>",
    "url_base": { ... },
    "database": {
      "host": "192.168.1.90",
      "port": 5434,
      "user": "scott",
      "password": "...",
      "database": "stock_quotes"
    }
  },
  "tickers": {
    "DIGITAL_CURRENCY_DAILY": ["GTC", "ETH", "XRP"],
    "TIME_SERIES_DAILY": ["QBTS", "IONQ", ...]
  }
}
```

## Database (PostgreSQL)

- **Host:** `192.168.1.90:5434`
- **Database:** `stock_quotes`
- **Driver:** `psycopg2-binary`

### Tables

| Table | Description |
|---|---|
| `quotes` | Daily close prices; range-partitioned by year (quotes_2016 … quotes_future) |
| `asset_indexes` | Index definitions (name, type, created_date, portfolio_value) |
| `index_members` | Member symbols per index with optional market_cap weight |
| `index_weights` | Computed share counts per symbol per index |
| `index_history` | Computed time-series index values; range-partitioned by year |

Tables are created automatically on first run via `QuoteDatabase.create_tables()`.

### Index types

- `EQUAL_WEIGHT` — equal dollar allocation across members at inception
- `CONSTANT` — price-weighted (constant shares per member)
- `MARKET_CAP` — market-cap weighted at inception

### Seeding index definitions

On first use (empty DB), `AssetIndex` falls back to `indexes.json`. To persist definitions to DB for future reads, call `db.save_index_definition(index_cfg)` for each entry, or add a seed step to `shak.py`.

## Index Definition Format (`indexes.json`)

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
