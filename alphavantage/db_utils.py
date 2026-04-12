#!/usr/bin/env -S poetry run python

import logging

import psycopg2
import psycopg2.extras
import numpy as np
import pandas as pd
from psycopg2 import Error


class QuoteDatabase:
    def __init__(self, config):
        """
        Represents a class that handles database configuration and initiates a connection
        to the database using initialization parameters.

        :param config: Configuration dictionary containing the necessary setup details
            for database connectivity.

        :ivar config: Extracted database-specific configuration details
            from the provided 'config' dictionary.
        :type config: dict
        :ivar connection: Represents the state of the database connection.
        :type connection: Optional[Connection]
        """
        self.config = config["configuration"]["database"]
        self.connection = None
        self.connect()

    def connect(self):
        """
        Establishes a connection to a PostgreSQL database using the provided configuration.
        It attempts to create a connection to the database and logs the status
        of the connection. If the connection fails, an exception is raised and the
        error is logged.

        :raises Error: If there is an issue connecting to the PostgreSQL database or with
            the provided configuration parameters.
        """
        try:
            self.connection = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                dbname=self.config["database"]
            )
            self.connection.autocommit = False
            logging.info("Successfully connected to PostgreSQL database")
        except Error as e:
            logging.error(f"Error connecting to PostgreSQL database: {e}")
            raise

    def create_tables(self):
        """
        Creates necessary database tables if they do not already exist.

        Creates the partitioned `quotes` table (range-partitioned by date), yearly
        partitions for known data years plus a future catch-all, and all index-related
        tables (asset_indexes, index_members, index_weights, index_history with its
        own partitions).

        :raises Error: If there is any issue executing the SQL commands or committing
            the changes.
        :return: None
        """
        try:
            cursor = self.connection.cursor()

            # Partitioned quotes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    date      DATE          NOT NULL,
                    symbol    VARCHAR(20)   NOT NULL,
                    namespace VARCHAR(20)   NOT NULL,
                    close     NUMERIC(20,6),
                    currency  VARCHAR(10),
                    PRIMARY KEY (date, symbol, namespace)
                ) PARTITION BY RANGE (date)
            """)

            # Yearly partitions for quotes
            for year in range(2016, 2027):
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS quotes_{year}
                        PARTITION OF quotes
                        FOR VALUES FROM ('{year}-01-01') TO ('{year + 1}-01-01')
                """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotes_future
                    PARTITION OF quotes
                    FOR VALUES FROM ('2027-01-01') TO ('9999-12-31')
            """)

            # Index definition table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS asset_indexes (
                    id              SERIAL PRIMARY KEY,
                    name            VARCHAR(255) UNIQUE NOT NULL,
                    type            VARCHAR(20)  NOT NULL,
                    created_date    DATE         NOT NULL,
                    portfolio_value NUMERIC(20,6)
                )
            """)

            # Index member symbols
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS index_members (
                    index_id   INT          NOT NULL
                                REFERENCES asset_indexes(id) ON DELETE CASCADE,
                    symbol     VARCHAR(20)  NOT NULL,
                    market_cap NUMERIC(15,3),
                    position   SMALLINT,
                    PRIMARY KEY (index_id, symbol)
                )
            """)

            # Computed portfolio weights (shares per symbol)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS index_weights (
                    index_id INT          NOT NULL
                                REFERENCES asset_indexes(id) ON DELETE CASCADE,
                    symbol   VARCHAR(20)  NOT NULL,
                    shares   NUMERIC(20,8) NOT NULL,
                    PRIMARY KEY (index_id, symbol)
                )
            """)

            # Partitioned index history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS index_history (
                    index_id INT           NOT NULL
                                REFERENCES asset_indexes(id) ON DELETE CASCADE,
                    date     DATE          NOT NULL,
                    value    NUMERIC(20,6) NOT NULL,
                    PRIMARY KEY (index_id, date)
                ) PARTITION BY RANGE (date)
            """)

            for year in range(2025, 2027):
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS index_history_{year}
                        PARTITION OF index_history
                        FOR VALUES FROM ('{year}-01-01') TO ('{year + 1}-01-01')
                """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS index_history_future
                    PARTITION OF index_history
                    FOR VALUES FROM ('2027-01-01') TO ('9999-12-31')
            """)

            self.connection.commit()
            logging.info("Tables created successfully")
        except Error as e:
            logging.error(f"Error creating tables: {e}")
            self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

    # ------------------------------------------------------------------
    # Quote methods
    # ------------------------------------------------------------------

    def save_quotes(self, df):
        """
        Save multiple stock quotes from a DataFrame into the database.

        Uses a bulk upsert: inserts rows and updates `close` on conflict with
        the (date, symbol, namespace) primary key.

        :param df: A pandas DataFrame containing stock quotes to be saved.
                   Must include the columns: 'date', 'symbol', 'namespace',
                   'close', and 'currency'.
        :type df: pandas.DataFrame
        :return: None
        :raises Error: If an error occurs while interacting with the database.
        """
        try:
            cursor = self.connection.cursor()

            records = df.to_records(index=True)
            data = [(record.index, record.symbol, record.namespace,
                     float(record.close), record.currency) for record in records]

            psycopg2.extras.execute_values(
                cursor,
                """
                INSERT INTO quotes (date, symbol, namespace, close, currency)
                VALUES %s
                ON CONFLICT (date, symbol, namespace)
                DO UPDATE SET close = EXCLUDED.close
                """,
                data
            )
            self.connection.commit()
            logging.info(f"Successfully saved {len(data)} quotes to database")
        except Error as e:
            logging.error(f"Error saving quotes to database: {e}")
            self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

    def read_quotes(self, start_date=None, end_date=None, symbols=None):
        """
        Reads financial quotes from the database with optional filters.

        :param start_date: Optional lower bound for date (inclusive).
        :param end_date: Optional upper bound for date (inclusive).
        :param symbols: Optional list of ticker symbols to filter on.
        :return: A pandas DataFrame with columns date, symbol, namespace, close, currency.
        :rtype: pandas.DataFrame
        :raises Error: If an error occurs while querying the database.
        """
        try:
            cursor = self.connection.cursor()

            query = "SELECT date, symbol, namespace, close, currency FROM quotes"
            conditions = []
            params = []

            if start_date:
                conditions.append("date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("date <= %s")
                params.append(end_date)
            if symbols:
                placeholders = ', '.join(['%s'] * len(symbols))
                conditions.append(f"symbol IN ({placeholders})")
                params.extend(symbols)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY date, symbol"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            df = pd.DataFrame(rows, columns=["date", "symbol", "namespace", "close", "currency"])
            df["date"] = pd.to_datetime(df["date"])
            logging.info(f"Successfully read {len(df)} quotes from database")
            return df
        except Error as e:
            logging.error(f"Error reading quotes from database: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    # ------------------------------------------------------------------
    # Index definition methods
    # ------------------------------------------------------------------

    def save_index_definition(self, index_cfg: dict, portfolio_value: float = 10000.0):
        """
        Upsert an index definition and its members into the database.

        Replaces member rows on conflict so the member list stays current.

        :param index_cfg: Index config dict with keys NAME, TYPE, CREATED_DATE,
                          MEMBERS, and optionally MARKET_CAP.
        :param portfolio_value: Initial dollar value used when computing weights.
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                INSERT INTO asset_indexes (name, type, created_date, portfolio_value)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name)
                DO UPDATE SET type = EXCLUDED.type,
                              created_date = EXCLUDED.created_date,
                              portfolio_value = EXCLUDED.portfolio_value
                RETURNING id
            """, (index_cfg["NAME"], index_cfg["TYPE"],
                  index_cfg["CREATED_DATE"], portfolio_value))
            index_id = cursor.fetchone()[0]

            # Replace members
            cursor.execute("DELETE FROM index_members WHERE index_id = %s", (index_id,))
            market_caps = index_cfg.get("MARKET_CAP", [])
            members_data = [
                (index_id, symbol, market_caps[i] if i < len(market_caps) else None, i)
                for i, symbol in enumerate(index_cfg["MEMBERS"])
            ]
            psycopg2.extras.execute_values(
                cursor,
                "INSERT INTO index_members (index_id, symbol, market_cap, position) VALUES %s",
                members_data
            )

            self.connection.commit()
            logging.info(f"Saved index definition: {index_cfg['NAME']}")
        except Error as e:
            logging.error(f"Error saving index definition: {e}")
            self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

    def read_index_definitions(self) -> dict:
        """
        Read all index definitions from the database.

        Returns a dict in the same format as indexes.json so AssetIndex can
        consume it without modification.

        :return: {"asset_indexes": [...]} matching the indexes.json schema.
        :rtype: dict
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT ai.id, ai.name, ai.type, ai.created_date, ai.portfolio_value
                FROM asset_indexes ai
                ORDER BY ai.id
            """)
            index_rows = cursor.fetchall()

            result = []
            for index_id, name, itype, created_date, portfolio_value in index_rows:
                cursor.execute("""
                    SELECT symbol, market_cap
                    FROM index_members
                    WHERE index_id = %s
                    ORDER BY position
                """, (index_id,))
                members_rows = cursor.fetchall()

                entry = {
                    "NAME": name,
                    "TYPE": itype,
                    "CREATED_DATE": created_date.isoformat(),
                    "MEMBERS": [r[0] for r in members_rows],
                }
                market_caps = [float(r[1]) for r in members_rows if r[1] is not None]
                if market_caps:
                    entry["MARKET_CAP"] = market_caps

                result.append(entry)

            logging.info(f"Read {len(result)} index definitions from database")
            return {"asset_indexes": result}
        except Error as e:
            logging.error(f"Error reading index definitions: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    # ------------------------------------------------------------------
    # Index weight methods
    # ------------------------------------------------------------------

    def save_index_weights(self, index_name: str, portfolio: dict):
        """
        Persist the computed portfolio weights (shares per symbol) for an index.

        :param index_name: The index name as stored in asset_indexes.name.
        :param portfolio: Dict mapping symbol → shares (float).
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute("SELECT id FROM asset_indexes WHERE name = %s", (index_name,))
            row = cursor.fetchone()
            if row is None:
                logging.warning(f"Index '{index_name}' not found; skipping weight save")
                return
            index_id = row[0]

            data = [(index_id, symbol, shares) for symbol, shares in portfolio.items()]
            psycopg2.extras.execute_values(
                cursor,
                """
                INSERT INTO index_weights (index_id, symbol, shares)
                VALUES %s
                ON CONFLICT (index_id, symbol)
                DO UPDATE SET shares = EXCLUDED.shares
                """,
                data
            )
            self.connection.commit()
            logging.info(f"Saved weights for index '{index_name}'")
        except Error as e:
            logging.error(f"Error saving index weights: {e}")
            self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

    def read_index_weights(self, index_name: str) -> dict:
        """
        Return the cached portfolio weights for an index.

        :param index_name: Index name.
        :return: Dict mapping symbol → shares, or empty dict if not found.
        :rtype: dict
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT iw.symbol, iw.shares
                FROM index_weights iw
                JOIN asset_indexes ai ON ai.id = iw.index_id
                WHERE ai.name = %s
            """, (index_name,))
            rows = cursor.fetchall()
            return {symbol: float(shares) for symbol, shares in rows}
        except Error as e:
            logging.error(f"Error reading index weights: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    # ------------------------------------------------------------------
    # Index history methods
    # ------------------------------------------------------------------

    def save_index_history(self, index_name: str, series: pd.Series):
        """
        Persist computed time-series index values for an index.

        :param index_name: Index name as stored in asset_indexes.name.
        :param series: Pandas Series with a DatetimeIndex and float values.
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute("SELECT id FROM asset_indexes WHERE name = %s", (index_name,))
            row = cursor.fetchone()
            if row is None:
                logging.warning(f"Index '{index_name}' not found; skipping history save")
                return
            index_id = row[0]

            data = [(index_id, date.date() if hasattr(date, 'date') else date, float(value))
                    for date, value in series.dropna().items()]

            psycopg2.extras.execute_values(
                cursor,
                """
                INSERT INTO index_history (index_id, date, value)
                VALUES %s
                ON CONFLICT (index_id, date)
                DO UPDATE SET value = EXCLUDED.value
                """,
                data
            )
            self.connection.commit()
            logging.info(f"Saved {len(data)} history rows for index '{index_name}'")
        except Error as e:
            logging.error(f"Error saving index history: {e}")
            self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

    def read_index_history(self, index_name: str,
                           start_date=None, end_date=None) -> pd.Series:
        """
        Return the stored time-series values for an index.

        :param index_name: Index name.
        :param start_date: Optional lower bound (inclusive).
        :param end_date: Optional upper bound (inclusive).
        :return: Pandas Series indexed by date, or empty Series if no data.
        :rtype: pandas.Series
        """
        try:
            cursor = self.connection.cursor()

            query = """
                SELECT ih.date, ih.value
                FROM index_history ih
                JOIN asset_indexes ai ON ai.id = ih.index_id
                WHERE ai.name = %s
            """
            params = [index_name]

            if start_date:
                query += " AND ih.date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND ih.date <= %s"
                params.append(end_date)
            query += " ORDER BY ih.date"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                return pd.Series(dtype=float)

            dates, values = zip(*rows)
            return pd.Series([float(v) for v in values],
                             index=pd.to_datetime(list(dates)),
                             name=index_name)
        except Error as e:
            logging.error(f"Error reading index history: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def close(self):
        """
        Closes the active database connection if it exists and is currently open.

        :return: None
        """
        if self.connection and self.connection.closed == 0:
            self.connection.close()
            logging.info("Database connection closed")
