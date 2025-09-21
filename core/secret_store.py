import os, json, base64
from typing import Optional, Dict
from cryptography.fernet import Fernet

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(ROOT, "data")
KEY_PATH = os.path.join(DATA_DIR, ".secrets_key")
STORE_PATH = os.path.join(DATA_DIR, "secrets.enc")

def _ensure_key() -> bytes:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f: f.write(key)
    return open(KEY_PATH, "rb").read()

def _fernet() -> Fernet:
    return Fernet(_ensure_key())

def set_user_secret(user_id: str, key: str, value: str) -> None:
    f = _fernet()
    store: Dict[str, Dict[str, str]] = {}
    if os.path.exists(STORE_PATH):
        store = json.load(open(STORE_PATH, "r", encoding="utf-8"))
    user = store.get(user_id) or {}
    token = f.encrypt(value.encode("utf-8")).decode("utf-8")
    user[key] = token
    store[user_id] = user
    json.dump(store, open(STORE_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def get_user_secret(user_id: str, key: str) -> Optional[str]:
    if not os.path.exists(STORE_PATH): return None
    store = json.load(open(STORE_PATH, "r", encoding="utf-8"))
    user = store.get(user_id) or {}
    token = user.get(key)
    if not token: return None
    f = _fernet()
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return None

def get_user_all(user_id: str) -> Dict[str, str]:
    if not os.path.exists(STORE_PATH): return {}
    store = json.load(open(STORE_PATH, "r", encoding="utf-8"))
    f = _fernet()
    out = {}
    for k, v in (store.get(user_id) or {}).items():
        try:
            out[k] = f.decrypt(v.encode("utf-8")).decode("utf-8")
        except Exception:
            out[k] = None
    return out
