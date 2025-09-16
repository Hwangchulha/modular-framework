from typing import Dict, Any
from .. import _store  # fixed relative import

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    act = envelope.get("action")
    body = envelope.get("input", {})

    if act == "REGISTER":
        uid = _store.create_user(body.get("email"), body.get("password"), body.get("nickname"))
        return {"ok": True, "mode":"SINGLE", "data":{"user_id": uid}}

    # 아래는 토큰이 있어야 (auth:profile 스코프) 접근 가능
    uid = (ctx or {}).get("user_id")
    if not uid:
        return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"no token"}}

    if act == "GET":
        u = _store.get_user_by_id(uid)
        if not u:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"unknown user"}}
        return {"ok": True, "mode":"SINGLE", "data":{"id": u["id"], "email": u["email"], "nickname": u.get("nickname")}}

    if act == "UPDATE":
        _store.update_profile(uid, body.get("nickname"))
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True}}

    return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unsupported action"}}
