"""SQLite helpers: connection and schema creation."""
import os
import sqlite3

import config


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql: str, params=(), one: bool = False):
    """Run a SELECT and return dict rows (or a single dict / None)."""
    conn = get_db()
    try:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql: str, params=()) -> int:
    """Run INSERT/UPDATE/DELETE and return lastrowid."""
    conn = get_db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def init_db():
    """Create the tables. A database from an older version of this project (users, energy columns) is cleaned up first."""
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = get_db()
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(predictions)").fetchall()]
        if cols and ("user_id" in cols or "pump_status" not in cols):   # older layout: recreate (rows were only test predictions)
            conn.execute("DROP TABLE predictions")
        conn.execute("DROP TABLE IF EXISTS users")
        conn.execute("DROP TABLE IF EXISTS contact_messages")
        with open(config.SCHEMA_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
        dcols = [r[1] for r in conn.execute("PRAGMA table_info(datasets)").fetchall()]
        if "system_params" not in dcols:
            conn.execute("ALTER TABLE datasets ADD COLUMN system_params TEXT")
        conn.commit()
    finally:
        conn.close()
