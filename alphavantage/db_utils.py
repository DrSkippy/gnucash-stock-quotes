#!/usr/bin/env -S poetry run python

import logging
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime

class QuoteDatabase:
    def __init__(self, config):
        """Initialize database connection using configuration from tickers.json"""
        self.config = config["configuration"]["database"]
        self.connection = None
        self.connect()

    def connect(self):
        """Establish database connection"""
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
        """Create necessary tables if they don't exist"""
        try:
            cursor = self.connection.cursor()
            
            # Create quotes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    date DATE,
                    symbol VARCHAR(20),
                    namespace VARCHAR(20),
                    close DECIMAL(20,6),
                    currency VARCHAR(10),
                    PRIMARY KEY (date, symbol, namespace)
                )
            """)
            
            self.connection.commit()
            logging.info("Tables created successfully")
        except Error as e:
            logging.error(f"Error creating tables: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def save_quotes(self, df):
        """Save quotes from DataFrame to database"""
        try:
            cursor = self.connection.cursor()
            
            # Convert DataFrame to list of tuples for insertion
            records = df.to_records(index=True)
            insert_query = """
                INSERT INTO quotes (date, symbol, namespace, close, currency)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                close = VALUES(close)
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
        """Read quotes from database with optional date and symbol filters"""
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
            
            df = pd.read_sql(query, self.connection, params=params)
            df.set_index('date', inplace=True)
            logging.info(f"Successfully read {len(df)} quotes from database")
            return df
        except Error as e:
            logging.error(f"Error reading quotes from database: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logging.info("Database connection closed") 