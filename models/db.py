# ============================================================
# models/db.py — Database Connection Helper
# ============================================================
# Provides a simple get_connection() helper so every module
# can obtain a fresh MySQL connection using the shared config.
# ============================================================

import mysql.connector
from mysql.connector import Error
from config import Config


def get_connection():
    """
    Opens and returns a MySQL connection using credentials
    defined in config.py.

    Returns:
        mysql.connector.connection.MySQLConnection | None
    """
    try:
        connection = mysql.connector.connect(
            host     = Config.DB_HOST,
            port     = Config.DB_PORT,
            user     = Config.DB_USER,
            password = Config.DB_PASSWORD,
            database = Config.DB_NAME
        )
        return connection
    except Error as e:
        print(f"[DB ERROR] Could not connect to MySQL: {e}")
        return None


def execute_query(query: str, params: tuple = (), fetch: bool = False):
    """
    Utility to run a single parameterised query.

    Args:
        query  : SQL string with %s placeholders.
        params : Tuple of values for placeholders.
        fetch  : If True, returns all fetched rows.

    Returns:
        list[dict] | True | None
    """
    connection = get_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)

        if fetch:
            result = cursor.fetchall()
            return result

        connection.commit()
        return cursor.lastrowid   # useful for INSERT operations

    except Error as e:
        print(f"[DB ERROR] Query failed: {e}")
        connection.rollback()
        return None

    finally:
        cursor.close()
        connection.close()
