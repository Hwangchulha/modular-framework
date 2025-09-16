from typing import Dict, Any
from modules.auth import _store
from core import jwt_utils
from core.ratelimit import LOGIN_EMAIL_LIMITER, LOGIN_IP_LIMITER

DEFAULT_SCOPES = ["auth:profile"]

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    act = envelope.get("action")
    body = envelope.get("input", {})

    if act == "LOGIN":
        email = body.get("email","").strip().lower()
        ip = (ctx or {}).get("client_ip","-")
        if not LOGIN_EMAIL_LIMITER.allow(f"e:{email}") or not LOGIN_IP_LIMITER.allow(f"ip:{ip}"):
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_RATE_LIMIT","message":"too many login attempts"}}
        u = _store.verify_password(email, body.get("password",""))
        if not u:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"invalid credentials"}}
        scopes = list(DEFAULT_SCOPES)
        access = jwt_utils.issue_access(u["id"], scopes=scopes, minutes=30)
        refresh = _store.create_refresh(u["id"], days=(30 if body.get("remember_me") else 1))
        return {"ok": True, "mode":"SINGLE", "data":{"access_token": access, "refresh_token": refresh, "scopes": scopes}}

    if act == "REFRESH":
        rt = body.get("refresh_token","")
        rec = _store.get_refresh(rt)
        if not rec:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"invalid refresh"}}
        # rotate token
        new_rt = _store.rotate_refresh(rt, rec["user_id"], days=30)
        access = jwt_utils.issue_access(rec["user_id"], scopes=DEFAULT_SCOPES, minutes=30)
        return {"ok": True, "mode":"SINGLE", "data":{"access_token": access, "refresh_token": new_rt}}

    if act == "LOGOUT":
        _store.revoke_refresh(body.get("refresh_token",""))
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True}}

    if act == "WHOAMI":
        uid = (ctx or {}).get("user_id")
        if not uid:
            return {"ok": True, "mode":"SINGLE", "data":{"id": None, "email": None, "nickname": None, "role": None, "scopes": []}}
        u = _store.get_user_by_id(uid)
        return {"ok": True, "mode":"SINGLE", "data":{"id": u.get("id"), "email": u.get("email"), "nickname": u.get("nickname"), "role": u.get("role","user"), "scopes": DEFAULT_SCOPES}}

    return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unsupported action"}}
