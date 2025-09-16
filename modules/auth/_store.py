import os, sqlite3, time, hashlib, secrets
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "data", "auth.db")
DB_PATH = os.path.abspath(DB_PATH)

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init():
    c = _conn()
    cur = c.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        nickname TEXT,
        pw_hash TEXT,
        pw_salt TEXT,
        created_at INTEGER
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS refresh_tokens(
        token TEXT PRIMARY KEY,
        user_id TEXT,
        expires_at INTEGER,
        created_at INTEGER
    )""")
    c.commit(); c.close()

def _hash_pw(password: str, salt: str) -> str:
    h = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 120_000)
    return h.hex()

def create_user(email: str, password: str, nickname: str) -> str:
    init()
    uid = secrets.token_hex(16)
    salt = secrets.token_hex(16)
    pw_hash = _hash_pw(password, salt)
    now = int(time.time())
    with _conn() as c:
        c.execute("INSERT INTO users(id,email,nickname,pw_hash,pw_salt,created_at) VALUES(?,?,?,?,?,?)",
                  (uid,email,nickname,pw_hash,salt,now))
    return uid

def get_user_by_email(email: str) -> Optional[Dict[str,Any]]:
    init()
    with _conn() as c:
        r = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
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
            # expired -> delete
            c.execute("DELETE FROM refresh_tokens WHERE token=?", (token,))
            return None
        return rec

def revoke_refresh(token: str):
    init()
    with _conn() as c:
        c.execute("DELETE FROM refresh_tokens WHERE token=?", (token,))
