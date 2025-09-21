from typing import Dict, Any
from core import secret_store

KEYS = ["app_key","app_secret","account_no","product_code","is_paper","custtype"]

def _uid(ctx):
    return (ctx or {}).get("user_id")

async def run(envelope: Dict[str, Any], ctx=None, env=None) -> Dict[str, Any]:
    act = envelope.get("action")
    body = envelope.get("input", {})

    uid = _uid(ctx)
    if not uid:
        return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_FORBIDDEN","message":"no token"}}

    if act == "SET":
        for k in KEYS:
            v = body.get(k)
            if v is None: 
                return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":f"missing {k}"}}
        secret_store.set_user_secret(uid, "KIS_APP_KEY", body["app_key"])
        secret_store.set_user_secret(uid, "KIS_APP_SECRET", body["app_secret"])
        secret_store.set_user_secret(uid, "KIS_ACCOUNT_NO", body["account_no"])
        secret_store.set_user_secret(uid, "KIS_PRODUCT_CODE", body["product_code"])
        secret_store.set_user_secret(uid, "KIS_IS_PAPER", "1" if body["is_paper"] else "0")
        secret_store.set_user_secret(uid, "KIS_CUSTTYPE", body["custtype"])
        return {"ok": True, "mode":"SINGLE", "data":{"ok": True}}

    if act == "GET":
        app_key = secret_store.get_user_secret(uid, "KIS_APP_KEY") or ""
        account_no = secret_store.get_user_secret(uid, "KIS_ACCOUNT_NO") or ""
        product_code = secret_store.get_user_secret(uid, "KIS_PRODUCT_CODE") or "01"
        is_paper = (secret_store.get_user_secret(uid, "KIS_IS_PAPER") or "1") == "1"
        custtype = secret_store.get_user_secret(uid, "KIS_CUSTTYPE") or "P"
        return {"ok": True, "mode":"SINGLE", "data":{
            "app_key": app_key[:4] + "****" if app_key else "",
            "account_no": account_no,
            "product_code": product_code,
            "is_paper": is_paper,
            "custtype": custtype
        }}

    return {"ok": False, "mode":"SINGLE", "error":{"code":"ERR_SCHEMA","message":"unsupported action"}}
