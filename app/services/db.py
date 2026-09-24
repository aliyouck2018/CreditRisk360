"""Database connection helpers (psycopg2, Supabase-compatible)."""
import decimal
import psycopg2
import psycopg2.extras
from flask import current_app


def get_conn():
    """Return a raw psycopg2 connection (per-request cached by Flask context)."""
    if not hasattr(current_app, "_db_conn") or current_app._db_conn is None or current_app._db_conn.closed:
        url = current_app.config["DATABASE_URL"]
        # Supabase URLs may use ssl; ensure it works for both local and remote
        current_app._db_conn = psycopg2.connect(url, sslmode="prefer")
    return current_app._db_conn


def get_db():
    """Return a RealDictCursor factory for dict-style rows."""
    conn = get_conn()
    return conn


def query(sql, params=None, one=False):
    """Execute a SELECT and return list of dict rows (or single dict)."""
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or ())
        rows = cur.fetchall()
    rows = [_convert(row) for row in rows]
    if one:
        return rows[0] if rows else None
    return rows


def _convert(value):
    """Recursively convert Decimals to floats (py3.14 strictness safety)."""
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return type(value)(_convert(v) for v in value) if isinstance(value, list) else tuple(_convert(v) for v in value)
    if isinstance(value, dict):
        return {k: _convert(v) for k, v in value.items()}
    if hasattr(value, "items") and not isinstance(value, str):
        try:
            items = value.items()
            return type(value)(**({k: _convert(v) for k, v in items})) if not isinstance(value, RealDictRow) else RealDictRow({k: _convert(v) for k, v in items})
        except Exception:
            return value
    return value


def execute(sql, params=None):
    """Execute a write statement and commit."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
    conn.commit()