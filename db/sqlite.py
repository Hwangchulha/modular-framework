
import os, sqlite3
from typing import Any, Iterable

_CONN = None
_DB_PATH = None

def _parse_db_url() -> str:
    url = os.getenv("DB_URL", "").strip()
    if not url or url.startswith("sqlite:///"):
        # default sqlite path
        if not url:
            url = "sqlite:///data/app.db"
        return url.replace("sqlite:///", "", 1)
    # For now only sqlite is supported in this helper
    raise RuntimeError("Only sqlite DB_URL is supported in this scaffold. Use format sqlite:///data/app.db")

def _ensure_dir(fp: str):
    d = os.path.dirname(fp)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)

def conn() -> sqlite3.Connection:
    global _CONN, _DB_PATH
    if _CONN is None:
        _DB_PATH = _parse_db_url()
        _ensure_dir(_DB_PATH)
        _CONN = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
    return _CONN

def init_basic_schema():
    c = conn()
    c.execute("""
    CREATE TABLE IF NOT EXISTS auth_users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    c.commit()

def execute(sql: str, params: Iterable[Any] | None = None):
    cur = conn().cursor()
    cur.execute(sql, tuple(params or ()))
    conn().commit()
    return cur

def query_one(sql: str, params: Iterable[Any] | None = None):
    cur = conn().cursor()
    cur.execute(sql, tuple(params or ()))
    return cur.fetchone()

def query_all(sql: str, params: Iterable[Any] | None = None):
    cur = conn().cursor()
    cur.execute(sql, tuple(params or ()))
    return cur.fetchall()
