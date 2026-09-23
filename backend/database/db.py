import sqlite3
import os
import contextlib
from typing import Generator, Any, Dict, List, Optional

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.environ.get("DATABASE_PATH", os.path.join(DB_DIR, "farm.db"))
SCHEMA_FILE = os.path.join(DB_DIR, "schema.sql")

def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
    """Converts a SQLite query row into a standard Python dictionary."""
    fields = [col[0] for col in cursor.description]
    return {key: value for key, value in zip(fields, row)}

@contextlib.contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for obtaining a database connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = dict_factory
    # Enable WAL mode for high concurrency and zero locking issues
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(force: bool = False) -> None:
    """Initializes the database using schema.sql."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    with get_db() as conn:
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema_script = f.read()
        conn.executescript(schema_script)
    print(f"[DB] Initialized database at: {DB_FILE}")

def log_audit(
    action: str,
    module: str,
    record_id: Optional[str] = None,
    details: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> None:
    """Records an audit log entry. If conn is provided, executes within the active transaction."""
    sql = """
        INSERT INTO audit_logs (user_id, username, action, module, record_id, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    params = (
        user_id or 1,
        username or "admin",
        action,
        module,
        str(record_id) if record_id else None,
        details or ""
    )
    if conn:
        conn.execute(sql, params)
    else:
        with get_db() as local_conn:
            local_conn.execute(sql, params)

if __name__ == "__main__":
    init_db()
