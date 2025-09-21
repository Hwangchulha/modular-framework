from typing import Dict, Any
import sqlite3, os
from modules.auth import _store

def _db_path():
    return _store.DB_PATH

def _has_column(cur, table, col):
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    for r in rows:
        if str(r[1]).lower() == col.lower():
            return True
    return False

def _migrate() -> Dict[str, Any]:
    _store.init()  # ensure tables
    changed = []
    with sqlite3.connect(_db_path()) as c:
        cur = c.cursor()
        # role column
        if not _has_column(cur, "users", "role"):
            cur.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            changed.append("users.role += TEXT DEFAULT 'user'")
        # normalize hint only (no destructive update)
        c.commit()
    return {"changed": changed, "db_path": _db_path()}

def _check() -> Dict[str, Any]:
    with sqlite3.connect(_db_path()) as c:
        cur = c.cursor()
        tbls = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        cols = {}
        for t in tbls:
            info = cur.execute(f"PRAGMA table_info({t})").fetchall()
            cols[t] = [str(r[1]) for r in info]
        return {"tables": tbls, "columns": cols, "db_path": _db_path()}

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    act = envelope.get("action")
    if act == "MIGRATE":
        details = _migrate()
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True, "details": details}}
    if act == "CHECK":
        details = _check()
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True, "details": details}}
    return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unsupported action"}}
