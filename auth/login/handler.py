from typing import Dict, Any
from .. import _store  # fixed relative import
from core import jwt_utils

DEFAULT_SCOPES = ["auth:profile"]

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    act = envelope.get("action")
    body = envelope.get("input", {})

    if act == "LOGIN":
        u = _store.verify_password(body.get("email",""), body.get("password",""))
        if not u:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"invalid credentials"}}
        scopes = list(DEFAULT_SCOPES)
        access = jwt_utils.issue_access(u["id"], scopes=scopes, minutes=30)
        refresh = _store.create_refresh(u["id"], days=(30 if body.get("remember_me") else 1))
        return {"ok": True, "mode":"SINGLE", "data":{"access_token": access, "refresh_token": refresh, "scopes": scopes}}

    if act == "REFRESH":
        rec = _store.get_refresh(body.get("refresh_token",""))
        if not rec:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"invalid refresh"}}
        access = jwt_utils.issue_access(rec["user_id"], scopes=DEFAULT_SCOPES, minutes=30)
        return {"ok": True, "mode":"SINGLE", "data":{"access_token": access}}

    if act == "LOGOUT":
        _store.revoke_refresh(body.get("refresh_token",""))
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True}}

    if act == "WHOAMI":
        uid = (ctx or {}).get("user_id")
        if not uid:
            return {"ok": True, "mode":"SINGLE", "data":{"id": None, "email": None, "nickname": None, "scopes": []}}
        u = _store.get_user_by_id(uid)
        return {"ok": True, "mode":"SINGLE", "data":{"id": u.get("id"), "email": u.get("email"), "nickname": u.get("nickname"), "scopes": DEFAULT_SCOPES}}

    return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unsupported action"}}
