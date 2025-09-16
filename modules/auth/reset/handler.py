from typing import Dict, Any
from modules.auth import _store
import secrets

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    act = envelope.get("action")
    body = envelope.get("input", {})

    if act == "REQUEST":
        # for demo, generate simple code and return (production: send email/SMS)
        email = body.get("email")
        if not _store.get_user_by_email(email):
            # avoid leakage: pretend ok but no code
            return {"ok": True, "mode":"SINGLE", "data":{"code": ""}}
        code = str(secrets.randbelow(900000) + 100000)  # 6-digit
        _store.create_reset(email, code, ttl_min=10)
        return {"ok": True, "mode":"SINGLE", "data":{"code": code}}

    if act == "CONFIRM":
        email = body.get("email"); code = body.get("code"); newpw = body.get("new_password")
        if not _store.consume_reset(email, code):
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"invalid or expired code"}}
        u = _store.get_user_by_email(email)
        if not u:
            return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unknown email"}}
        _store.change_password(u["id"], newpw)
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True}}

    return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unsupported action"}}
