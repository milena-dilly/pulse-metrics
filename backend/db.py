"""
db.py — DuckDB connection manager
──────────────────────────────────
Single read-only connection to analytics.duckdb.
dbt is the ONLY writer. FastAPI is read-only.

Design:
  - One module-level connection (DuckDB is embedded, no pool needed)
  - Context manager for safe cursor use
  - Helper execute() that always returns list[dict]
"""

import os
import duckdb
from pathlib import Path
from contextlib import contextmanager
from typing import Any

# ── Config ───────────────────────────────────────────────────────────────────
# Override via env var in production / Docker
DB_PATH = Path(os.getenv("DUCKDB_PATH", "analytics.duckdb")).resolve()

# DuckDB read-only connection — safe for concurrent FastAPI requests
# read_only=True prevents accidental writes and allows multi-process access
_conn: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """Returns the module-level read-only connection, creating it if needed."""
    global _conn
    if _conn is None:
        if not DB_PATH.exists():
            raise FileNotFoundError(
                f"DuckDB file not found at: {DB_PATH}\n"
                "Run `dbt build` to generate analytics.duckdb first."
            )
        _conn = duckdb.connect(str(DB_PATH), read_only=True)
    return _conn


@contextmanager
def get_cursor():
    """
    Context manager that yields a DuckDB cursor.
    Handles connection errors gracefully.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def query(sql: str, params: list[Any] | None = None) -> list[dict]:
    """
    Execute a SQL query and return results as a list of dicts.

    Args:
        sql:    SQL string (use $1, $2 for params)
        params: optional list of bind parameters

    Returns:
        list of row dicts — empty list if no results

    Example:
        rows = query("SELECT * FROM marts.fact_revenue WHERE month = $1", ["2024-06"])
    """
    with get_cursor() as cur:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def query_one(sql: str, params: list[Any] | None = None) -> dict | None:
    """Execute a query and return the first row as dict, or None."""
    results = query(sql, params)
    return results[0] if results else None
