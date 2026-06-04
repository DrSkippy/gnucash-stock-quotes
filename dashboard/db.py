"""DB helpers for the dashboard.

Config is built entirely from environment variables so the container can be
deployed from Dockge (or any central location) without a mounted tickers.json.

Required env vars:
  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

Optional (only needed for the Fetch Latest Quotes action):
  AV_API_KEY
  TICKERS_STOCKS   — comma-separated, e.g. "AAPL,MSFT,SPY"
  TICKERS_CRYPTO   — comma-separated, e.g. "GTC,ETH,XRP"

Each callback opens a fresh psycopg2 connection, does its work, and closes it.
psycopg2 connections are not thread-safe; one per callback is the simplest
correct approach for a low-traffic internal tool.
"""

import os
import sys
from contextlib import contextmanager

# Project root on path so alphavantage package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alphavantage.db_utils import QuoteDatabase

# Alpha Vantage URL templates — public, not secrets
_AV_URL_BASE = {
    "DIGITAL_CURRENCY_DAILY": (
        "https://www.alphavantage.co/query"
        "?function=DIGITAL_CURRENCY_DAILY&symbol={}&market=USD&apikey={}"
    ),
    "TIME_SERIES_DAILY": (
        "https://www.alphavantage.co/query"
        "?function=TIME_SERIES_DAILY&symbol={}&apikey={}"
    ),
}

_config: dict | None = None


def _build_config() -> dict:
    """Assemble the tickers.json-equivalent dict from environment variables."""
    stocks = [s.strip() for s in os.environ.get("TICKERS_STOCKS", "").split(",") if s.strip()]
    crypto = [s.strip() for s in os.environ.get("TICKERS_CRYPTO", "").split(",") if s.strip()]
    return {
        "configuration": {
            "key": os.environ.get("AV_API_KEY", ""),
            "url_base": _AV_URL_BASE,
            "database": {
                "host": os.environ.get("DB_HOST", "192.168.1.90"),
                "port": int(os.environ.get("DB_PORT", "5434")),
                "user": os.environ["DB_USER"],
                "password": os.environ["DB_PASSWORD"],
                "database": os.environ.get("DB_NAME", "stock_quotes"),
            },
        },
        "tickers": {
            "DIGITAL_CURRENCY_DAILY": crypto,
            "TIME_SERIES_DAILY": stocks,
        },
    }


def get_config() -> dict:
    global _config
    if _config is None:
        _config = _build_config()
    return _config


@contextmanager
def get_db():
    """Yield a QuoteDatabase instance and close it on exit."""
    db = QuoteDatabase(get_config())
    try:
        yield db
    finally:
        db.close()


def get_all_symbols() -> list[str]:
    """Return sorted list of every distinct symbol in the quotes table."""
    with get_db() as db:
        cursor = db.connection.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM quotes ORDER BY symbol")
        rows = cursor.fetchall()
        cursor.close()
    return [r[0] for r in rows]


def get_index_meta(db: QuoteDatabase, index_name: str) -> dict:
    """Return full metadata row for one index (includes portfolio_value)."""
    cursor = db.connection.cursor()
    cursor.execute(
        "SELECT name, type, created_date, portfolio_value FROM asset_indexes WHERE name = %s",
        (index_name,),
    )
    row = cursor.fetchone()
    cursor.close()
    if not row:
        return {}
    return {
        "name": row[0],
        "type": row[1],
        "created_date": str(row[2]),
        "portfolio_value": float(row[3]) if row[3] else 10_000.0,
    }


def get_last_quote_date() -> str:
    """Return the most recent date in the quotes table as a string."""
    with get_db() as db:
        cursor = db.connection.cursor()
        cursor.execute("SELECT MAX(date) FROM quotes")
        row = cursor.fetchone()
        cursor.close()
    return str(row[0]) if row and row[0] else "N/A"
