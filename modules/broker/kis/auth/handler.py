from typing import Dict, Any
import os, json, time
import requests
from core import secret_store

def _conf(uid: str):
    app_key = secret_store.get_user_secret(uid, "KIS_APP_KEY")
    app_secret = secret_store.get_user_secret(uid, "KIS_APP_SECRET")
    is_paper = (secret_store.get_user_secret(uid, "KIS_IS_PAPER") or "1") == "1"
    base = "https://openapivts.koreainvestment.com:29443" if is_paper else "https://openapi.koreainvestment.com:9443"
    token_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", f"kist_{uid}.json")
    token_file = os.path.abspath(token_file)
    return app_key, app_secret, is_paper, base, token_file

def _load_cached(token_file):
    try:
        d = json.load(open(token_file, "r", encoding="utf-8"))
        if d.get("exp",0) > time.time()+60:
            return d.get("access_token")
    except Exception:
        pass
    return None

def _save_cached(token_file, token, ttl_sec):
    os.makedirs(os.path.dirname(token_file), exist_ok=True)
    json.dump({"access_token": token, "exp": time.time()+ttl_sec}, open(token_file, "w", encoding="utf-8"))

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    uid = (ctx or {}).get("user_id")
    if not uid:
        return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"no token"}}

    app_key, app_secret, is_paper, base, token_file = _conf(uid)
    if not app_key or not app_secret:
        return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SECRET","message":"KIS app key/secret not set"}}

    tok = _load_cached(token_file)
    if tok:
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True, "source":"cache"}}

    url = base + ("/oauth2/token" if is_paper else "/oauth2/tokenP")
    body = {"grant_type":"client_credentials", "appkey": app_key, "appsecret": app_secret}
    try:
        r = requests.post(url, json=body, timeout=10)
        j = r.json()
        if "access_token" in j:
            ttl = int(j.get("expires_in", 3600))
            _save_cached(token_file, j["access_token"], ttl)
            return {"ok": True, "mode":"SINGLE", "data":{"ok": True, "source":"network"}}
        else:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message": j}}
    except Exception as e:
        return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_INTERNAL","message": str(e)}}
