# ============================================================
# models/db.py — Database Connection Helper (PostgreSQL)
# ============================================================

import os
import psycopg2
import psycopg2.extras
from config import Config


def get_connection():
    """
    Opens and returns a PostgreSQL connection using the
    DATABASE_URL from config.py (injected by Render Blueprint).

    Returns:
        psycopg2 connection | None
    """
    try:
        connection = psycopg2.connect(Config.DATABASE_URL, sslmode="require")
        return connection
    except Exception as e:
        print(f"[DB ERROR] Could not connect to PostgreSQL: {e}")
        return None


def execute_query(query: str, params: tuple = (), fetch: bool = False):
    """
    Utility to run a single parameterised query.

    Args:
        query  : SQL string with %s placeholders.
        params : Tuple of values for placeholders.
        fetch  : If True, returns all fetched rows as list of dicts.

    Returns:
        list[dict] | int | None
    """
    connection = get_connection()
    if not connection:
        return None

    try:
        # RealDictCursor returns rows as dicts (same behaviour as mysql-connector)
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, params)

        if fetch:
            result = [dict(row) for row in cursor.fetchall()]
            return result

        connection.commit()
        return cursor.lastrowid if hasattr(cursor, "lastrowid") else True

    except Exception as e:
        print(f"[DB ERROR] Query failed: {e}")
        connection.rollback()
        return None

    finally:
        cursor.close()
        connection.close()
