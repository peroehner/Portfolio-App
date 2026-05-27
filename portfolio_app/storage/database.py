"""SQLite connection and schema initialization."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from portfolio_app.config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    last_portfolio_id INTEGER,
    last_login_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    shares REAL NOT NULL,
    avg_cost REAL NOT NULL,
    purchase_date TEXT,
    target_price REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    UNIQUE (portfolio_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_positions_portfolio
    ON positions (portfolio_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_portfolios_user_updated
    ON portfolios (user_id, updated_at DESC);
"""


def ensure_db_dir():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    ensure_db_dir()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    with get_connection() as conn:
        conn.executescript(_SCHEMA)
        _run_schema_migrations(conn)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_status ON users (status, email)"
        )


def _run_schema_migrations(conn: sqlite3.Connection):
    """Backfill columns for pre-user-management SQLite files."""
    user_cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    if "display_name" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    if "status" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    if "last_login_at" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")

    # Backfill defaults for legacy rows.
    conn.execute(
        """
        UPDATE users
        SET display_name = COALESCE(
            NULLIF(display_name, ''),
            substr(email, 1, CASE WHEN instr(email, '@') > 1 THEN instr(email, '@') - 1 ELSE length(email) END)
        )
        """
    )
    conn.execute("UPDATE users SET status = COALESCE(NULLIF(status, ''), 'active')")
