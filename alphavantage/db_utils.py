#!/usr/bin/env -S poetry run python

import logging

import mysql.connector
import numpy as np
import pandas as pd
from mysql.connector import Error


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
        Establishes a connection to a MySQL database using the provided configuration.
        It attempts to create a connection to the database and logs the status
        of the connection. If the connection fails, an exception is raised and the
        error is logged.

        :raises Error: If there is an issue connecting to the MySQL database or with
            the provided configuration parameters.
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"]
            )
            if self.connection.is_connected():
                logging.info("Successfully connected to MySQL database")
        except Error as e:
            logging.error(f"Error connecting to MySQL database: {e}")
            raise

    def create_tables(self):
        """
        Creates necessary database tables if they do not already exist.

        This function establishes a connection with the database, then creates
        the `quotes` table if it does not exist. The table includes fields for
        date, symbol, namespace, close value, and currency, with a composite
        primary key on the fields `date`, `symbol`, and `namespace`. After
        successful execution, the changes are committed to the database.

        :param self:
            Represents the instance of the class through which the function
            is invoked.
        :raises:
            Error: If there is any issue executing the SQL command or committing
            the changes, the exception is logged and re-raised.
        :return:
            None
        """
        try:
            cursor = self.connection.cursor()

            # Create quotes table
            cursor.execute("""CREATE TABLE IF NOT EXISTS quotes
            (   date
                DATE,
                symbol
                VARCHAR ( 20 ),
                namespace VARCHAR ( 20 ),
                close DECIMAL ( 20, 6 ),
                currency VARCHAR ( 10 ),
                PRIMARY KEY ( date, symbol, namespace ) ) """)

            self.connection.commit()
            logging.info("Tables created successfully")
        except Error as e:
            logging.error(f"Error creating tables: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def save_quotes(self, df):
        """
        Save multiple stock quotes from a DataFrame into the database.

        The method utilizes a database connection to batch insert stock quote
        data into the database. The data is sourced from a given DataFrame
        and converted into a format compatible with the SQL insertion query.
        If a record with the same primary key exists, it updates the relevant
        fields. The operation is transactional, and an exception is raised
        if an error occurs during the process.

        :param df: A pandas DataFrame containing stock quotes to be saved.
                   Must include the columns: 'date', 'symbol', 'namespace',
                   'close', and 'currency'.
        :type df: pandas.DataFrame
        :return: None
        :raises mysql.connector.Error: If an error occurs while interacting
                                       with the database.
        """
        try:
            cursor = self.connection.cursor()

            # Convert DataFrame to list of tuples for insertion
            records = df.to_records(index=True)
            insert_query = """
                           INSERT INTO quotes (date, symbol, namespace, close, currency)
                           VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY
                           UPDATE close =
                           VALUES (close) \
                           """

            # Prepare data for insertion
            data = [(record.index, record.symbol, record.namespace,
                     record.close, record.currency) for record in records]

            cursor.executemany(insert_query, data)
            self.connection.commit()
            logging.info(f"Successfully saved {len(data)} quotes to database")
        except Error as e:
            logging.error(f"Error saving quotes to database: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def read_quotes(self, start_date=None, end_date=None, symbols=None):
        """
        Reads financial quotes from a database, allowing for optional filters on date range
        and symbols. The data is retrieved in the form of a DataFrame and includes columns
        for date, symbol, namespace, close, and currency. The method can handle filtering
        by start date, end date, or a list of specific symbols.

        :param start_date: Optional; Filters quotes where the date is greater than or equal
            to this value. Must be a valid date.
        :param end_date: Optional; Filters quotes where the date is less than or equal to
            this value. Must be a valid date.
        :param symbols: Optional; A list of symbols to filter the quotes. Each symbol
            within the list must be a string.
        :return: A pandas DataFrame containing the requested quotes, with columns for date,
            symbol, namespace, close, and currency.
        :rtype: pandas.DataFrame
        :raises Error: If an error occurs while querying the database or fetching the data.
        """
        try:
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

            df = pd.read_sql(query, self.connection, params=params, parse_dates=["date"])
            logging.info(f"Successfully read {len(df)} quotes from database")
            return df
        except Error as e:
            logging.error(f"Error reading quotes from database: {e}")
            raise

    def close(self):
        """
        Closes the active database connection if it exists and is currently open.

        This function ensures that the database connection, if it exists and is still
        open, is properly closed to release resources and maintain system stability.
        After successfully closing the connection, an informational log message is
        recorded indicating the closure of the connection.

        :return: None
        """
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logging.info("Database connection closed")
