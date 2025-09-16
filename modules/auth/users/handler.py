from typing import Dict, Any
from modules.auth import _store

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    act = envelope.get("action")
    body = envelope.get("input", {})

    if act == "REGISTER":
        try:
            uid = _store.create_user(body.get("email"), body.get("password"), body.get("nickname"))
            return {"ok": True, "mode":"SINGLE", "data":{"user_id": uid}}
        except ValueError as ve:
            if "email exists" in str(ve):
                return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"email exists"}}
            raise

    # token required
    uid = (ctx or {}).get("user_id")
    if not uid:
        return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"no token"}}

    if act == "GET":
        u = _store.get_user_by_id(uid)
        if not u:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"unknown user"}}
        return {"ok": True, "mode":"SINGLE", "data":{"id": u["id"], "email": u["email"], "nickname": u.get("nickname"), "role": u.get("role","user")}}

    if act == "UPDATE":
        _store.update_profile(uid, body.get("nickname"))
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True}}

    if act == "CHANGE_PASSWORD":
        # verify old
        u = _store.verify_password(_store.get_user_by_id(uid)["email"], body.get("old_password"))
        if not u:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"old password mismatch"}}
        _store.change_password(uid, body.get("new_password"))
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True}}

    return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unsupported action"}}
