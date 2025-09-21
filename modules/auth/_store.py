import os, sqlite3, time, hashlib, secrets
from typing import Optional, Dict, Any, List

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DB_PATH = os.path.join(ROOT, "data", "auth.db")

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _hash_pw(password: str, salt: str) -> str:
    h = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 150_000)
    return h.hex()

def _norm(email: str) -> str:
    return (email or '').strip().lower()

def _has_column(cur, table: str, column: str) -> bool:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    for r in rows:
        if str(r[1]).lower() == column.lower():
            return True
    return False

def _ensure_tables_and_migrate():
    with _conn() as c:
        cur = c.cursor()
        # users table — create if missing
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            nickname TEXT,
            pw_hash TEXT,
            pw_salt TEXT,
            created_at INTEGER
        )""")
        # add role column if missing
        if not _has_column(cur, "users", "role"):
            try:
                cur.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            except Exception:
                pass

        # refresh_tokens table
        cur.execute("""CREATE TABLE IF NOT EXISTS refresh_tokens(
            token TEXT PRIMARY KEY,
            user_id TEXT,
            expires_at INTEGER,
            created_at INTEGER
        )""")

        # reset_tokens table (for password reset)
        cur.execute("""CREATE TABLE IF NOT EXISTS reset_tokens(
            token TEXT PRIMARY KEY,
            email TEXT,
            code_hash TEXT,
            expires_at INTEGER,
            created_at INTEGER
        )""")
        c.commit()

def init():
    _ensure_tables_and_migrate()

def email_exists(email: str) -> bool:
    init()
    with _conn() as c:
        r = c.execute("SELECT 1 FROM users WHERE lower(email)=?", (_norm(email),)).fetchone()
        return bool(r)

def create_user(email: str, password: str, nickname: str) -> str:
    init()
    nemail = _norm(email)
    if email_exists(nemail):
        raise ValueError("email exists")
    uid = secrets.token_hex(16)
    salt = secrets.token_hex(16)
    pw_hash = _hash_pw(password, salt)
    now = int(time.time())
    with _conn() as c:
        c.execute("INSERT INTO users(id,email,nickname,role,pw_hash,pw_salt,created_at) VALUES(?,?,?,?,?,?,?)",
                  (uid,nemail,nickname,'user',pw_hash,salt,now))
    return uid

def get_user_by_email(email: str) -> Optional[Dict[str,Any]]:
    init()
    with _conn() as c:
        r = c.execute("SELECT * FROM users WHERE lower(email)=?", (_norm(email),)).fetchone()
        return dict(r) if r else None

def get_user_by_id(uid: str) -> Optional[Dict[str,Any]]:
    init()
    with _conn() as c:
        r = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(r) if r else None

def verify_password(email: str, password: str) -> Optional[Dict[str,Any]]:
    u = get_user_by_email(email)
    if not u: return None
    if _hash_pw(password, u["pw_salt"]) != u["pw_hash"]: return None
    return u

def update_profile(uid: str, nickname: str):
    init()
    with _conn() as c:
        c.execute("UPDATE users SET nickname=? WHERE id=?", (nickname, uid))

def change_password(uid: str, new_password: str):
    init()
    salt = secrets.token_hex(16)
    pw_hash = _hash_pw(new_password, salt)
    with _conn() as c:
        c.execute("UPDATE users SET pw_hash=?, pw_salt=? WHERE id=?", (pw_hash, salt, uid))

def create_refresh(user_id: str, days: int = 30) -> str:
    init()
    tok = secrets.token_urlsafe(32)
    now = int(time.time())
    exp = now + days*86400
    with _conn() as c:
        c.execute("INSERT INTO refresh_tokens(token,user_id,expires_at,created_at) VALUES(?,?,?,?)",
                  (tok, user_id, exp, now))
    return tok

def get_refresh(token: str) -> Optional[Dict[str,Any]]:
    init()
    with _conn() as c:
        r = c.execute("SELECT * FROM refresh_tokens WHERE token=?", (token,)).fetchone()
        if not r: return None
        rec = dict(r)
        if rec["expires_at"] < int(time.time()):
            c.execute("DELETE FROM refresh_tokens WHERE token=?", (token,))
            return None
        return rec

def rotate_refresh(old_token: str, user_id: str, days: int = 30) -> str:
    init()
    new_tok = secrets.token_urlsafe(32)
    now = int(time.time())
    exp = now + days*86400
    with _conn() as c:
        c.execute("DELETE FROM refresh_tokens WHERE token=?", (old_token,))
        c.execute("INSERT INTO refresh_tokens(token,user_id,expires_at,created_at) VALUES(?,?,?,?)",
                  (new_tok, user_id, exp, now))
    return new_tok

def revoke_refresh(token: str):
    init()
    with _conn() as c:
        c.execute("DELETE FROM refresh_tokens WHERE token=?", (token,))

# ---- password reset helpers ----
def _hash_code(code: str) -> str:
    import hashlib as _hl
    return _hl.sha256(code.encode("utf-8")).hexdigest()

def create_reset(email: str, code: str, ttl_min: int = 10) -> str:
    init()
    tok = secrets.token_urlsafe(16)
    now = int(time.time())
    exp = now + ttl_min*60
    ch = _hash_code(code)
    with _conn() as c:
        c.execute("INSERT INTO reset_tokens(token,email,code_hash,expires_at,created_at) VALUES(?,?,?,?,?)",
                  (tok, _norm(email), ch, exp, now))
    return tok

def consume_reset(email: str, code: str) -> bool:
    init()
    ch = _hash_code(code)
    with _conn() as c:
        r = c.execute("SELECT token,expires_at FROM reset_tokens WHERE email=? AND code_hash=? ORDER BY created_at DESC LIMIT 1",
                      (_norm(email), ch)).fetchone()
        if not r: return False
        if int(r["expires_at"]) < int(time.time()):
            c.execute("DELETE FROM reset_tokens WHERE token=?", (r["token"],))
            return False
        c.execute("DELETE FROM reset_tokens WHERE token=?", (r["token"],))
        return True
