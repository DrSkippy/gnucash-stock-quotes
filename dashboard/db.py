"""Thin helpers that wrap QuoteDatabase for dashboard use.

Each function opens a fresh connection, does its work, and closes it.
psycopg2 connections are not thread-safe; creating one per callback is the
simplest correct approach for a low-traffic internal tool.
"""

import json
import os
import sys
from contextlib import contextmanager

# Project root on path so alphavantage package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alphavantage.db_utils import QuoteDatabase

_CONFIG_PATH = os.environ.get("TICKERS_CONFIG", "tickers.json")
_config: dict | None = None


def _load_config() -> dict:
    global _config
    if _config is None:
        with open(_CONFIG_PATH) as f:
            _config = json.load(f)
    return _config


@contextmanager
def get_db():
    """Yield a QuoteDatabase instance and close it on exit."""
    db = QuoteDatabase(_load_config())
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
